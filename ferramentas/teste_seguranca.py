"""
Teste de seguranca do broker (teste 4 do plano de testes).

Faz tres tentativas que DEVEM ser recusadas pelo EMQX:
  1. conectar sem usuario e senha;
  2. conectar com a senha errada;
  3. publicar com o usuario de leitura (dashboard).

Uso:
    python teste_seguranca.py          (usa config.ini da mesma pasta)

O resultado aparece na tela e e salvo em ../evidencias/teste_seguranca_<data>.txt
"""

import argparse
import configparser
import ssl
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt

PASTA = Path(__file__).resolve().parent
ESPERA = 10  # segundos


def novo_cliente(m, nome):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"teste-{nome}-{int(time.time()) % 100000}",
                    protocol=mqtt.MQTTv5)
    if m.getboolean("tls", fallback=True):
        ca = m.get("ca", fallback="").strip()
        if ca:
            ca_path = Path(ca) if Path(ca).is_absolute() else PASTA / ca
            c.tls_set(ca_certs=str(ca_path), tls_version=ssl.PROTOCOL_TLS_CLIENT)
        else:
            c.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
    return c


def tentar_conectar(m, usuario, senha, nome):
    """Retorna (conectou, descricao)."""
    c = novo_cliente(m, nome)
    if usuario is not None:
        c.username_pw_set(usuario, senha)
    resultado = {}
    pronto = threading.Event()

    def ao_conectar(cl, ud, flags, codigo, props):
        resultado["ok"] = not codigo.is_failure
        resultado["codigo"] = str(codigo)
        pronto.set()

    def ao_desconectar(cl, ud, flags, codigo, props):
        if "ok" not in resultado:
            resultado["ok"] = False
            resultado["codigo"] = f"conexao encerrada pelo broker ({codigo})"
        pronto.set()

    c.on_connect = ao_conectar
    c.on_disconnect = ao_desconectar
    try:
        c.connect(m.get("host"), m.getint("porta", fallback=8883), keepalive=30)
    except Exception as e:  # recusa na camada de rede/TLS
        return False, f"erro ao conectar: {e}", None
    c.loop_start()
    if not pronto.wait(ESPERA):
        resultado.setdefault("ok", False)
        resultado.setdefault("codigo", "sem resposta do broker")
    if not resultado["ok"]:
        c.loop_stop()
        return False, resultado["codigo"], None
    return True, resultado["codigo"], c


def main():
    parser = argparse.ArgumentParser(description="Testa se o broker recusa acessos indevidos.")
    parser.add_argument("--config", default=str(PASTA / "config.ini"))
    args = parser.parse_args()

    cfg = configparser.ConfigParser()
    cfg.BOOLEAN_STATES.update({"sim": True, "nao": False, "não": False})
    if not cfg.read(args.config, encoding="utf-8"):
        sys.exit("config.ini nao encontrado. Copie config.example.ini para config.ini e preencha.")
    m = cfg["mqtt"]
    t = cfg["teste_seguranca"]
    base = m.get("topico_base", "detector-gas")
    usuario_leitura = t.get("usuario_leitura")
    senha_leitura = t.get("senha_leitura")

    linhas = [f"Teste de seguranca do broker {m.get('host')}:{m.get('porta')}",
              f"Data: {datetime.now():%d/%m/%Y %H:%M:%S}", ""]
    aprovados = 0

    def registrar(n, descricao, recusado, detalhe):
        nonlocal aprovados
        situacao = "RECUSADO (esperado)" if recusado else "ACEITO (FALHA DE SEGURANCA)"
        if recusado:
            aprovados += 1
        texto = f"{n}. {descricao}\n   Resultado: {situacao}\n   Detalhe do broker: {detalhe}\n"
        print(texto)
        linhas.append(texto)

    # 1. Sem usuario e senha
    ok, codigo, c = tentar_conectar(m, None, None, "anonimo")
    if c:
        c.disconnect(); c.loop_stop()
    registrar(1, "Conectar sem usuario e senha", not ok, codigo)

    # 2. Senha errada
    ok, codigo, c = tentar_conectar(m, usuario_leitura, "senha-errada-123", "senhaerrada")
    if c:
        c.disconnect(); c.loop_stop()
    registrar(2, f"Conectar com o usuario '{usuario_leitura}' e senha errada", not ok, codigo)

    # 3. Publicar com o usuario de leitura
    ok, codigo, c = tentar_conectar(m, usuario_leitura, senha_leitura, "leitura")
    if not ok:
        linhas.append(f"3. Nao foi possivel testar a publicacao: o usuario '{usuario_leitura}' "
                      f"nao conectou ({codigo}). Confira a senha_leitura no config.ini.\n")
        print(linhas[-1])
    else:
        topico = f"{base}/teste-seguranca"
        marca = f"teste-{int(time.time())}"
        recebida = threading.Event()
        puback = {}
        caiu = threading.Event()

        def ao_receber(cl, ud, msg):
            if msg.payload.decode(errors="replace") == marca:
                recebida.set()

        def ao_publicar(cl, ud, mid, codigo_pub, props):
            puback["codigo"] = codigo_pub

        def ao_desconectar(cl, ud, flags, codigo_d, props):
            caiu.set()

        c.on_message = ao_receber
        c.on_publish = ao_publicar
        c.on_disconnect = ao_desconectar
        c.subscribe(topico, qos=1)
        time.sleep(1.5)
        c.publish(topico, marca, qos=1, retain=False)
        recebida.wait(5)
        time.sleep(1)  # da tempo do PUBACK chegar
        cod = puback.get("codigo")
        negado_puback = cod is not None and getattr(cod, "is_failure", False)
        bloqueado = (not recebida.is_set()) or negado_puback or caiu.is_set()
        detalhe = (f"PUBACK: {cod if cod is not None else 'nao recebido'}; "
                   f"mensagem {'CHEGOU' if recebida.is_set() else 'nao chegou'} ao topico; "
                   f"{'broker encerrou a conexao' if caiu.is_set() else 'conexao mantida'}")
        registrar(3, f"Publicar em {topico} com o usuario de leitura '{usuario_leitura}'",
                  bloqueado, detalhe)
        c.disconnect(); c.loop_stop()

    resumo = f"Resumo: {aprovados} de 3 tentativas indevidas recusadas."
    print(resumo)
    linhas.append(resumo)

    destino = PASTA.parent / "evidencias"
    destino.mkdir(exist_ok=True)
    arquivo = destino / f"teste_seguranca_{datetime.now():%Y%m%d_%H%M}.txt"
    arquivo.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"Resultado salvo em {arquivo}")


if __name__ == "__main__":
    main()
