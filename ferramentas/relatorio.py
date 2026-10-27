"""
Relatorio dos dados gravados pelo coletor.

Calcula as metricas usadas na Tabela 11 do paper (taxa de entrega, atraso,
alertas, quedas e reconexoes), exporta as leituras em CSV e gera o grafico
do nivel de gas com a linha do limite.

Uso:
    python relatorio.py                          (todo o banco)
    python relatorio.py --ultimos 60             (ultimos 60 minutos)
    python relatorio.py --inicio "2026-10-27 14:00" --fim "2026-10-27 15:00"
    python relatorio.py --nome teste1_ar_limpo   (nome da pasta de saida)

Saida (por padrao em ../evidencias/<nome>/):
    relatorio.md, leituras.csv, eventos.csv, grafico.png
"""

import argparse
import csv
import sqlite3
import statistics
import sys
from datetime import datetime
from pathlib import Path

PASTA = Path(__file__).resolve().parent


def ms_para_data(ms):
    return datetime.fromtimestamp(ms / 1000)


def fmt_hora(ms):
    return ms_para_data(ms).strftime("%d/%m/%Y %H:%M:%S")


def fmt_seg(ms):
    return f"{ms / 1000:.2f} s".replace(".", ",")


def pct(x):
    return f"{x:.1f}%".replace(".", ",")


def ler_data(texto):
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return int(datetime.strptime(texto, formato).timestamp() * 1000)
        except ValueError:
            pass
    sys.exit(f"Data invalida: {texto}  (use por exemplo 2026-10-27 14:30)")


def segmentos_por_seq(leituras):
    """Separa as leituras em trechos continuos de seq (o seq volta a 0 quando a placa reinicia)."""
    segmentos, atual = [], []
    for r in leituras:
        if atual and r["seq"] is not None and atual[-1]["seq"] is not None and r["seq"] < atual[-1]["seq"]:
            segmentos.append(atual)
            atual = []
        atual.append(r)
    if atual:
        segmentos.append(atual)
    return segmentos


def episodios_de_alerta(leituras):
    eps, inicio, pico = [], None, 0
    for r in leituras:
        if r["critico"] and inicio is None:
            inicio, pico = r, r["nivel"]
        elif r["critico"] and inicio is not None:
            pico = max(pico, r["nivel"])
        elif not r["critico"] and inicio is not None:
            eps.append({"inicio": inicio["t_ms"], "fim": r["t_ms"], "pico": pico, "limite": inicio["limite"]})
            inicio = None
    if inicio is not None:
        eps.append({"inicio": inicio["t_ms"], "fim": leituras[-1]["t_ms"], "pico": pico,
                    "limite": inicio["limite"], "aberto": True})
    return eps


def quedas_do_detector(eventos):
    """Pares offline -> online do topico de status (tempo ate o detector voltar)."""
    quedas, offline_em = [], None
    for e in eventos:
        if e["tipo"] != "status_detector":
            continue
        if e["valor"] == "offline" and offline_em is None:
            offline_em = e["recebido_ms"]
        elif e["valor"] == "online" and offline_em is not None:
            quedas.append({"offline": offline_em, "online": e["recebido_ms"]})
            offline_em = None
    if offline_em is not None:
        quedas.append({"offline": offline_em, "online": None})
    return quedas


def gerar_grafico(leituras, eps, quedas, caminho, titulo):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    # Quebra a linha onde faltam dados (mais de 3 s sem leitura), para nao ligar os pontos
    x, nivel, limite = [], [], []
    anterior = None
    for r in leituras:
        if anterior is not None and r["t_ms"] - anterior > 3000:
            x.append(ms_para_data(anterior + 1)); nivel.append(float("nan")); limite.append(float("nan"))
        x.append(ms_para_data(r["t_ms"])); nivel.append(r["nivel"]); limite.append(r["limite"])
        anterior = r["t_ms"]

    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=150)
    for i, ep in enumerate(eps):
        ax.axvspan(ms_para_data(ep["inicio"]), ms_para_data(ep["fim"]), color="#c4291c", alpha=0.12,
                   label="Alerta ativo" if i == 0 else None, linewidth=0)
    for i, q in enumerate(quedas):
        fim = q["online"] if q["online"] else max(q["offline"] + 1000, leituras[-1]["t_ms"])
        ax.axvspan(ms_para_data(q["offline"]), ms_para_data(fim), color="#888888", alpha=0.18,
                   label="Detector offline" if i == 0 else None, linewidth=0, hatch="//")
    ax.plot(x, nivel, color="#1d5fa8", linewidth=1.2, label="Nível de gás (ADC)")
    ax.step(x, limite, where="post", color="#c4291c", linewidth=1.4, linestyle="--", label="Limite")

    ax.set_ylim(0, 4095)
    ax.set_ylabel("Leitura do ADC (0 a 4095)")
    ax.set_xlabel("Horário")
    ax.set_title(titulo, fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    fig.autofmt_xdate()
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(caminho)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Gera o relatorio dos testes a partir do banco do coletor.")
    parser.add_argument("--banco", default=str(PASTA / "dados" / "detector.db"))
    parser.add_argument("--ultimos", type=float, help="considerar so os ultimos N minutos")
    parser.add_argument("--inicio", help='ex.: "2026-10-27 14:00"')
    parser.add_argument("--fim", help='ex.: "2026-10-27 15:00"')
    parser.add_argument("--nome", help="nome da pasta de saida dentro de evidencias/")
    parser.add_argument("--saida", help="pasta de saida (substitui --nome)")
    parser.add_argument("--intervalo", type=float, default=1.0,
                        help="intervalo de envio do firmware em segundos (padrao 1)")
    args = parser.parse_args()

    if not Path(args.banco).exists():
        sys.exit(f"Banco nao encontrado: {args.banco}. Rode o coletor.py primeiro.")

    banco = sqlite3.connect(args.banco)
    banco.row_factory = sqlite3.Row

    fim = ler_data(args.fim) if args.fim else None
    inicio = ler_data(args.inicio) if args.inicio else None
    if args.ultimos:
        fim = fim or int(datetime.now().timestamp() * 1000)
        inicio = fim - int(args.ultimos * 60_000)

    filtro, parametros = [], []
    if inicio is not None:
        filtro.append("recebido_ms >= ?"); parametros.append(inicio)
    if fim is not None:
        filtro.append("recebido_ms <= ?"); parametros.append(fim)
    where = (" WHERE " + " AND ".join(filtro)) if filtro else ""

    leituras = [dict(r) for r in banco.execute(
        f"SELECT * FROM leituras{where} ORDER BY recebido_ms, seq", parametros)]
    eventos = [dict(r) for r in banco.execute(
        f"SELECT * FROM eventos{where} ORDER BY recebido_ms", parametros)]

    if not leituras:
        sys.exit("Nenhuma leitura no periodo escolhido.")

    nome = args.nome or "relatorio_" + datetime.now().strftime("%Y%m%d_%H%M")
    saida = Path(args.saida) if args.saida else PASTA.parent / "evidencias" / nome
    saida.mkdir(parents=True, exist_ok=True)

    # ---------- Metricas ----------
    t0, t1 = leituras[0]["t_ms"], leituras[-1]["t_ms"]
    duracao_s = (t1 - t0) / 1000
    recebidas = len(leituras)

    segmentos = segmentos_por_seq(leituras)
    esperadas_seq = sum(seg[-1]["seq"] - seg[0]["seq"] + 1 for seg in segmentos
                        if seg[0]["seq"] is not None)
    unicas = len({(i, r["seq"]) for i, seg in enumerate(segmentos) for r in seg})
    duplicadas = recebidas - unicas
    taxa_seq = 100 * unicas / esperadas_seq if esperadas_seq else 0
    lacunas = []
    for seg in segmentos:
        for a, b in zip(seg, seg[1:]):
            if a["seq"] is not None and b["seq"] is not None and b["seq"] - a["seq"] > 1:
                lacunas.append((a, b, b["seq"] - a["seq"] - 1))

    esperadas_tempo = int(duracao_s / args.intervalo) + 1
    cobertura_tempo = 100 * min(unicas, esperadas_tempo) / esperadas_tempo if esperadas_tempo else 0

    atrasos = [r["recebido_ms"] - r["t_ms"] for r in leituras if r["t_ms"]]
    atraso_med = statistics.mean(atrasos)
    atraso_mediana = statistics.median(atrasos)
    atraso_max = max(atrasos)
    atraso_p95 = sorted(atrasos)[int(0.95 * (len(atrasos) - 1))]

    eps = episodios_de_alerta(leituras)
    quedas = quedas_do_detector(eventos)
    reinicios = len(segmentos) - 1
    nivel_min = min(r["nivel"] for r in leituras)
    nivel_max = max(r["nivel"] for r in leituras)
    nivel_medio = statistics.mean(r["nivel"] for r in leituras)
    limites = sorted({r["limite"] for r in leituras})

    # ---------- CSV ----------
    with open(saida / "leituras.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["hora_leitura", "hora_recebida", "atraso_ms", "dispositivo", "seq",
                    "nivel", "limite", "critico"])
        for r in leituras:
            w.writerow([fmt_hora(r["t_ms"]), fmt_hora(r["recebido_ms"]), r["recebido_ms"] - r["t_ms"],
                        r["dispositivo"], r["seq"], r["nivel"], r["limite"], r["critico"]])
    with open(saida / "eventos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["hora", "tipo", "valor"])
        for e in eventos:
            w.writerow([fmt_hora(e["recebido_ms"]), e["tipo"], e["valor"]])

    # ---------- Grafico ----------
    titulo = f"Nível de gás e limite, {ms_para_data(t0):%d/%m/%Y %H:%M} a {ms_para_data(t1):%H:%M}"
    gerar_grafico(leituras, eps, quedas, saida / "grafico.png", titulo)

    # ---------- Relatorio ----------
    L = []
    L.append(f"# Relatório do detector de gás: {nome}\n")
    L.append(f"Período: {fmt_hora(t0)} a {fmt_hora(t1)} ({duracao_s / 60:.1f} min)\n".replace(".", ","))
    L.append("## Transmissão e armazenamento\n")
    L.append("| Métrica | Valor |")
    L.append("| --- | --- |")
    L.append(f"| Mensagens gravadas no banco | {recebidas} |")
    L.append(f"| Mensagens esperadas pelo seq | {esperadas_seq} |")
    L.append(f"| Taxa de entrega pelo seq | {pct(taxa_seq)} |")
    L.append(f"| Mensagens esperadas pelo tempo (1 a cada {args.intervalo:g} s) | {esperadas_tempo} |")
    L.append(f"| Cobertura pelo tempo | {pct(cobertura_tempo)} |")
    L.append(f"| Lacunas no seq | {len(lacunas)} (total de {sum(n for *_, n in lacunas)} mensagens) |")
    L.append(f"| Mensagens duplicadas | {duplicadas} |")
    L.append(f"| Reinícios da placa (seq voltou a 0) | {reinicios} |")
    L.append("")
    L.append("## Atraso entre a leitura no ESP32 e a chegada ao coletor\n")
    L.append("Depende dos relógios do ESP32 (NTP) e do computador estarem sincronizados.\n")
    L.append("| Métrica | Valor |")
    L.append("| --- | --- |")
    L.append(f"| Médio | {fmt_seg(atraso_med)} |")
    L.append(f"| Mediana | {fmt_seg(atraso_mediana)} |")
    L.append(f"| 95% das mensagens abaixo de | {fmt_seg(atraso_p95)} |")
    L.append(f"| Máximo | {fmt_seg(atraso_max)} |")
    L.append("")
    L.append("## Leituras do sensor\n")
    L.append("| Métrica | Valor |")
    L.append("| --- | --- |")
    L.append(f"| Nível mínimo / médio / máximo | {nivel_min} / {nivel_medio:.0f} / {nivel_max} |")
    L.append(f"| Limite(s) usado(s) | {', '.join(map(str, limites))} |")
    L.append(f"| Episódios de alerta | {len(eps)} |")
    L.append("")
    if eps:
        L.append("| # | Início | Fim | Duração | Pico | Limite |")
        L.append("| --- | --- | --- | --- | --- | --- |")
        for i, ep in enumerate(eps, 1):
            fim_txt = fmt_hora(ep["fim"]) + (" (ainda ativo)" if ep.get("aberto") else "")
            L.append(f"| {i} | {fmt_hora(ep['inicio'])} | {fim_txt} | {fmt_seg(ep['fim'] - ep['inicio'])} "
                     f"| {ep['pico']} | {ep['limite']} |")
        L.append("")
    L.append("## Quedas e reconexões do detector (tópico de status)\n")
    if quedas:
        L.append("| # | Ficou offline | Voltou online | Tempo fora |")
        L.append("| --- | --- | --- | --- |")
        for i, q in enumerate(quedas, 1):
            if q["online"]:
                L.append(f"| {i} | {fmt_hora(q['offline'])} | {fmt_hora(q['online'])} "
                         f"| {fmt_seg(q['online'] - q['offline'])} |")
            else:
                L.append(f"| {i} | {fmt_hora(q['offline'])} | não voltou no período | |")
    else:
        L.append("Nenhuma queda registrada no período.")
    L.append("")
    if lacunas:
        L.append("## Lacunas no seq\n")
        L.append("| Depois de | Seq anterior | Seq seguinte | Mensagens faltando |")
        L.append("| --- | --- | --- | --- |")
        for a, b, n in lacunas[:50]:
            L.append(f"| {fmt_hora(a['t_ms'])} | {a['seq']} | {b['seq']} | {n} |")
        if len(lacunas) > 50:
            L.append(f"\n(mais {len(lacunas) - 50} lacunas no leituras.csv)")
        L.append("")
    L.append("Arquivos: leituras.csv, eventos.csv, grafico.png")

    (saida / "relatorio.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print("\n".join(L))
    print(f"\nArquivos salvos em: {saida}")


if __name__ == "__main__":
    main()
