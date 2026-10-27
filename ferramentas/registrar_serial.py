"""
Grava o monitor serial do ESP32 num arquivo, com a hora de cada linha.

Serve para o teste de 1 hora em ar limpo: no fim, mostra quantas leituras
foram feitas, quantas vezes a placa reiniciou e quantas vezes o MQTT falhou.

Uso (feche o Monitor Serial da Arduino IDE antes, a porta so abre em um lugar):
    python registrar_serial.py COM5            (Windows)
    python registrar_serial.py /dev/ttyACM0    (Linux)
    python registrar_serial.py --listar        (mostra as portas disponiveis)

Pare com Ctrl+C. O arquivo fica em ../evidencias/serial_<data>.log
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import serial
from serial.tools import list_ports

PASTA = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Grava o monitor serial do ESP32 com horario.")
    parser.add_argument("porta", nargs="?", help="ex.: COM5 ou /dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--listar", action="store_true", help="lista as portas seriais")
    parser.add_argument("--intervalo", type=float, default=0.5, help="intervalo de leitura do firmware (s)")
    args = parser.parse_args()

    if args.listar or not args.porta:
        portas = list(list_ports.comports())
        if not portas:
            print("Nenhuma porta serial encontrada. A placa esta conectada?")
        for p in portas:
            print(f"{p.device:15} {p.description}")
        if not args.porta:
            print("\nInforme a porta, por exemplo: python registrar_serial.py COM5")
        return

    destino = PASTA.parent / "evidencias"
    destino.mkdir(exist_ok=True)
    arquivo = destino / f"serial_{datetime.now():%Y%m%d_%H%M}.log"

    try:
        porta = serial.Serial(args.porta, args.baud, timeout=1)
    except serial.SerialException as e:
        sys.exit(f"Nao abriu {args.porta}: {e}\nO Monitor Serial da Arduino IDE esta aberto?")

    leituras = reinicios = falhas_mqtt = conexoes_mqtt = 0
    inicio = time.time()
    print(f"Gravando {args.porta} em {arquivo}  (Ctrl+C para parar)\n")

    with open(arquivo, "w", encoding="utf-8") as f:
        try:
            while True:
                bruta = porta.readline()
                if not bruta:
                    continue
                linha = bruta.decode("utf-8", errors="replace").rstrip()
                carimbo = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                f.write(f"{carimbo}  {linha}\n")
                f.flush()
                print(f"{carimbo[11:]}  {linha}")

                if linha.startswith("gas:"):
                    leituras += 1
                elif "Conectando ao Wi-Fi" in linha:
                    reinicios += 1
                elif "MQTT" in linha and "falhou" in linha:
                    falhas_mqtt += 1
                elif "MQTT" in linha and "conectado" in linha:
                    conexoes_mqtt += 1
        except KeyboardInterrupt:
            pass

    porta.close()
    duracao = time.time() - inicio
    esperadas = int(duracao / args.intervalo)
    resumo = [
        "",
        "Resumo do registro serial",
        f"  Arquivo:                {arquivo}",
        f"  Duracao:                {duracao / 60:.1f} min",
        f"  Leituras registradas:   {leituras}",
        f"  Leituras esperadas:     {esperadas} (1 a cada {args.intervalo:g} s)",
        f"  Aproveitamento:         {100 * leituras / esperadas:.1f}%" if esperadas else "",
        f"  Reinicios da placa:     {reinicios}",
        f"  Conexoes ao MQTT:       {conexoes_mqtt}",
        f"  Falhas de conexao MQTT: {falhas_mqtt}",
    ]
    texto = "\n".join(l for l in resumo if l != "")
    print("\n" + texto)
    with open(arquivo, "a", encoding="utf-8") as f:
        f.write("\n" + texto + "\n")


if __name__ == "__main__":
    main()
