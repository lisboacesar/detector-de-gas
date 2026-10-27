"""
Coletor de dados do detector de gas.

Assina os topicos do detector no broker MQTT (EMQX Cloud) e grava cada
mensagem num banco SQLite (dados/detector.db). E a camada de armazenamento
do sistema: o broker so guarda a ultima leitura, o coletor guarda o historico.

Uso:
    python coletor.py                 (usa config.ini da mesma pasta)
    python coletor.py --config outro.ini

Pare com Ctrl+C. Depois gere o relatorio com:  python relatorio.py
"""

import argparse
import configparser
import json
import signal
import sqlite3
import ssl
import sys
import time
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt

PASTA = Path(__file__).resolve().parent

ESQUEMA = """
CREATE TABLE IF NOT EXISTS leituras (
    recebido_ms INTEGER NOT NULL,   -- hora em que o coletor recebeu (ms desde 1970, UTC)
    dispositivo TEXT,                -- campo id
    seq         INTEGER,             -- numero sequencial da mensagem
    t_ms        INTEGER,             -- hora da leitura no ESP32 (ms desde 1970, UTC)
    nivel       INTEGER,             -- campo v (ADC 0 a 4095)
    limite      INTEGER,             -- campo l
    critico     INTEGER,             -- campo c (1 = alerta)
    bruto       TEXT                 -- mensagem original
);
CREATE INDEX IF NOT EXISTS idx_leituras_t ON leituras (t_ms);

CREATE TABLE IF NOT EXISTS eventos (
    recebido_ms INTEGER NOT NULL,
    tipo        TEXT NOT NULL,       -- status_detector, coletor_conectado, coletor_desconectado
    valor       TEXT
);
"""


def agora_ms():
    return int(time.time() * 1000)


def hora(ms):
    return datetime.fromtimestamp(ms / 1000).strftime("%H:%M:%S")


def carregar_config(caminho):
    cfg = configparser.ConfigParser()
    cfg.BOOLEAN_STATES.update({"sim": True, "nao": False, "não": False})
    if not cfg.read(caminho, encoding="utf-8"):
        sys.exit(f"Arquivo de configuracao nao encontrado: {caminho}\n"
                 f"Copie config.example.ini para config.ini e preencha.")
    return cfg


def abrir_banco(caminho):
    caminho = Path(caminho)
    if not caminho.is_absolute():
        caminho = PASTA / caminho
    caminho.parent.mkdir(parents=True, exist_ok=True)
    banco = sqlite3.connect(caminho, check_same_thread=False)
    banco.executescript(ESQUEMA)
    banco.commit()
    return banco, caminho


def main():
    parser = argparse.ArgumentParser(description="Grava as mensagens do detector num banco SQLite.")
    parser.add_argument("--config", default=str(PASTA / "config.ini"))
    args = parser.parse_args()

    cfg = carregar_config(args.config)
    m = cfg["mqtt"]
    base = m.get("topico_base", "detector-gas")
    topico_leitura = f"{base}/leitura"
    topico_status = f"{base}/status"

    banco, caminho_banco = abrir_banco(cfg.get("banco", "arquivo", fallback="dados/detector.db"))
    contagem = {"leituras": 0}

    def registrar_evento(tipo, valor=""):
        banco.execute("INSERT INTO eventos VALUES (?, ?, ?)", (agora_ms(), tipo, valor))
        banco.commit()

    def ao_conectar(cliente, userdata, flags, codigo, propriedades):
        if codigo.is_failure:
            print(f"[{hora(agora_ms())}] Falha ao conectar: {codigo}")
            return
        print(f"[{hora(agora_ms())}] Conectado ao broker. Assinando {base}/leitura e {base}/status")
        cliente.subscribe([(topico_leitura, 1), (topico_status, 1)])
        registrar_evento("coletor_conectado")

    def ao_desconectar(cliente, userdata, flags, codigo, propriedades):
        print(f"[{hora(agora_ms())}] Desconectado do broker ({codigo}). Tentando de novo...")
        registrar_evento("coletor_desconectado", str(codigo))

    def ao_receber(cliente, userdata, msg):
        recebido = agora_ms()
        texto = msg.payload.decode("utf-8", errors="replace")

        if msg.topic == topico_status:
            # Status retido = ultimo status guardado no broker (pode ser antigo)
            registrar_evento("status_retido" if msg.retain else "status_detector", texto)
            print(f"[{hora(recebido)}] Status do detector: {texto}"
                  + (" (mensagem retida)" if msg.retain else ""))
            return

        # A leitura retida e a ultima que o broker guardou (pode ser antiga):
        # nao entra no historico para nao distorcer as contagens.
        if msg.retain:
            return

        try:
            d = json.loads(texto)
        except json.JSONDecodeError:
            print(f"[{hora(recebido)}] Mensagem ignorada (nao e JSON): {texto[:80]}")
            return

        banco.execute(
            "INSERT INTO leituras VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (recebido, d.get("id"), d.get("seq"), d.get("t"), d.get("v"),
             d.get("l"), d.get("c"), texto),
        )
        banco.commit()
        contagem["leituras"] += 1

        atraso = f"{recebido - d['t']} ms" if isinstance(d.get("t"), int) else "?"
        estado = "CRITICO" if d.get("c") else "normal"
        print(f"[{hora(recebido)}] seq={d.get('seq')}  gas={d.get('v')}  limite={d.get('l')}  "
              f"{estado:8}  atraso={atraso}  total={contagem['leituras']}")

    cliente = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"coletor-{int(time.time()) % 100000}",
        protocol=mqtt.MQTTv311,
    )
    cliente.username_pw_set(m.get("usuario"), m.get("senha"))
    if m.getboolean("tls", fallback=True):
        ca = m.get("ca", fallback="").strip()
        if ca:
            ca_path = Path(ca) if Path(ca).is_absolute() else PASTA / ca
            cliente.tls_set(ca_certs=str(ca_path), tls_version=ssl.PROTOCOL_TLS_CLIENT)
        else:
            cliente.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
    cliente.on_connect = ao_conectar
    cliente.on_disconnect = ao_desconectar
    cliente.on_message = ao_receber
    cliente.reconnect_delay_set(min_delay=1, max_delay=10)

    def encerrar(*_):
        print(f"\nEncerrando. {contagem['leituras']} leituras gravadas em {caminho_banco}")
        registrar_evento("coletor_encerrado")
        cliente.disconnect()
        cliente.loop_stop()
        banco.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, encerrar)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, encerrar)

    host = m.get("host")
    porta = m.getint("porta", fallback=8883)
    print(f"Banco de dados: {caminho_banco}")
    print(f"Conectando a {host}:{porta} ...  (Ctrl+C para parar)")
    cliente.connect_async(host, porta, keepalive=30)
    cliente.loop_start()
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
