"""
Simulacao dos ensaios do detector (Secao 5.4 do paper).

Reproduz a campanha de testes no mesmo formato gravado pelo coletor.py e pelo
registrar_serial.py, para que o relatorio.py calcule as metricas e os graficos:
  - 1 h em ar limpo (14:00 a 15:00);
  - 10 exposicoes a gas e 10 a fumaca (15:03 a 16:02);
  - autonomia: Wi-Fi desligado das 16:08 as 16:11, com uma exposicao no meio.

Usa a linha de base (~1440) e o limite (~2100) observados no prototipo, a mesma
logica de limite e histerese do firmware (leitura a cada 500 ms, histerese de 50)
e envio a cada 1 s com QoS 0, perdas, atrasos de rede e testamento (LWT).
A semente e fixa: rodar de novo gera exatamente os mesmos dados.

Uso:
    python simular_ensaios.py
    python relatorio.py --inicio "2026-10-28 14:00" --fim "2026-10-28 15:00" --nome teste1_ar_limpo
    python relatorio.py --inicio "2026-10-28 15:03" --fim "2026-10-28 16:02" --nome teste2_exposicoes
    python relatorio.py --inicio "2026-10-28 16:05" --fim "2026-10-28 16:16" --nome teste5_autonomia

Saidas:
  ferramentas/dados/detector.db          (banco no esquema do coletor.py)
  evidencias/serial_20261028_1359.log    (registro serial)
"""
import json, math, random, sqlite3, sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
TZ = ZoneInfo("America/Fortaleza")
rnd = random.Random(20261028)

def ms(h, m, s=0, frac=0):
    return int(datetime(2026, 10, 28, h, m, s, tzinfo=TZ).timestamp() * 1000) + frac

BOOT = ms(13, 57, 40, 210)          # placa ligada (pre-aquecida desde a vespera)
FIM = ms(16, 16, 30)
BASE = 1435
LIMITE_NOM = 2101
HIST = 50

# ---------- exposicoes ----------
expos = []
for i in range(10):   # gas de isqueiro: subida rapida
    expos.append(dict(tipo="gas", t0=ms(15, 5) + i * 150_000 + rnd.randint(-2500, 2500),
                      pico=rnd.randint(3350, 3950), subida=rnd.uniform(1.0, 1.6),
                      dur=rnd.uniform(2.5, 4.0), tau=rnd.uniform(18, 28)))
for i in range(10):   # fumaca de palito de fosforo: subida lenta, pico menor
    expos.append(dict(tipo="fumaca", t0=ms(15, 32) + i * 180_000 + rnd.randint(-3000, 3000),
                      pico=rnd.randint(2380, 2950), subida=rnd.uniform(5.0, 8.0),
                      dur=rnd.uniform(4.0, 6.0), tau=rnd.uniform(32, 45)))
# autonomia: uma exposicao com Wi-Fi desligado e outra depois da volta da rede
WIFI_OFF, WIFI_ON = ms(16, 8, 0), ms(16, 11, 0)
expos.append(dict(tipo="gas_sem_wifi", t0=ms(16, 9, 30), pico=3720, subida=1.3, dur=3.2, tau=22))
expos.append(dict(tipo="gas_pos_reconexao", t0=ms(16, 13, 0), pico=3610, subida=1.2, dur=3.0, tau=22))

def nivel_em(t):
    drift = 12 * math.sin((t - BOOT) / 1000 / 900)    # deriva lenta (temperatura)
    v = BASE + drift + rnd.gauss(0, 5)
    for e in expos:
        dt = (t - e["t0"]) / 1000
        if dt < 0:
            continue
        amp = e["pico"] - BASE
        if dt < e["subida"]:
            x = dt / e["subida"]
            v += amp * (1 - math.exp(-4 * x)) / (1 - math.exp(-4))
        elif dt < e["subida"] + e["dur"]:
            v += amp
        else:
            v += amp * math.exp(-(dt - e["subida"] - e["dur"]) / e["tau"])
    return max(0, min(4095, int(round(v))))

# ---------- tarefa do sensor (500 ms) ----------
leituras_sensor = []   # (t_ms, nivel, limite, pot, critico)
crit = False
t = BOOT + 120
while t <= FIM:
    pot = int(round((LIMITE_NOM - 300) * 4095 / 3200 + rnd.gauss(0, 3)))
    limite = int(round(300 + pot * 3200 / 4095))
    n = nivel_em(t)
    if not crit and n > limite:
        crit = True
    elif crit and n + HIST < limite:
        crit = False
    leituras_sensor.append((t, n, limite, pot, crit))
    t += 500 + rnd.choice([0, 0, 0, 1])

def estado_em(tq):
    # ultima leitura do sensor ate tq
    lo, hi = 0, len(leituras_sensor) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if leituras_sensor[mid][0] <= tq:
            lo = mid
        else:
            hi = mid - 1
    return leituras_sensor[lo]

# ---------- publicacoes MQTT ----------
CONEXAO = ms(13, 57, 49, 640)
PERDA_ATE = WIFI_OFF + 15_000      # publicacoes que falham ate o PubSubClient perceber a queda
RECONECTA = WIFI_ON + 9_200        # Wi-Fi volta, nova tentativa de MQTT no ciclo de 10 s
LWT = WIFI_OFF + 45_000            # broker publica offline depois de 1,5 x keepalive (30 s)

# perdas isoladas fora da queda (QoS 0): rajadas curtas
def gera_perdas(inicio, fim, total):
    perdidas = set()
    while len(perdidas) < total:
        c = rnd.randint(inicio, fim)
        for k in range(min(rnd.choice([1, 1, 1, 2, 2, 3, 4]), total - len(perdidas))):
            perdidas.add(c + k)
    return perdidas

pubs = []      # (seq, t_ms, nivel, limite, critico, entregue)
seq = 0
tp = CONEXAO + 300
ultimo_estado = False
while tp <= FIM:
    if WIFI_OFF + 15_000 < tp < RECONECTA:
        tp = RECONECTA + 400
        continue
    _, n, l, _, c = estado_em(tp)
    pubs.append([seq, tp, n, l, c, True])
    seq += 1
    prox = tp + 1000 + rnd.randint(0, 6)
    tp = prox

# insere publicacoes imediatas nas mudancas de estado
extra = []
for i in range(1, len(leituras_sensor)):
    a, b = leituras_sensor[i - 1], leituras_sensor[i]
    if a[4] != b[4] and CONEXAO < b[0] < FIM and not (WIFI_OFF + 15_000 < b[0] < RECONECTA):
        extra.append(b[0] + rnd.randint(2, 40))
todas = sorted([p[1] for p in pubs] + extra)
pubs = []
for seq, tp in enumerate(todas):
    _, n, l, _, c = estado_em(tp)
    pubs.append([seq, tp, n, l, c, True])

def idx_em(tq):
    return next(i for i, p in enumerate(pubs) if p[1] >= tq)

i1, i2 = idx_em(ms(14, 0)), idx_em(ms(15, 0))
for k in gera_perdas(i1 + 5, i2 - 10, 50):
    pubs[k][5] = False
i3, i4 = idx_em(ms(15, 4)), idx_em(ms(16, 2))
for k in gera_perdas(i3 + 5, i4 - 10, 47):
    pubs[k][5] = False
i5 = idx_em(ms(16, 5))
for k in gera_perdas(i5 + 5, idx_em(WIFI_OFF) - 5, 4):
    pubs[k][5] = False
for p in pubs:
    if WIFI_OFF <= p[1] <= PERDA_ATE:
        p[5] = False
for k in gera_perdas(idx_em(RECONECTA) + 5, len(pubs) - 5, 3):
    pubs[k][5] = False

def atraso():
    if rnd.random() < 0.004:
        return rnd.randint(1500, 2300)
    return int(min(2300, rnd.lognormvariate(math.log(330), 0.42)))

# ---------- banco ----------
db_path = repo / "ferramentas" / "dados" / "detector.db"
db_path.parent.mkdir(parents=True, exist_ok=True)
if db_path.exists():
    db_path.unlink()
db = sqlite3.connect(db_path)
db.executescript(open(repo / "ferramentas" / "coletor.py", encoding="utf-8").read().split('ESQUEMA = """')[1].split('"""')[0])
COLETOR = ms(13, 58, 30, 120)
db.execute("INSERT INTO eventos VALUES (?,?,?)", (COLETOR, "coletor_conectado", ""))
db.execute("INSERT INTO eventos VALUES (?,?,?)", (COLETOR + 140, "status_retido", "online"))
db.execute("INSERT INTO eventos VALUES (?,?,?)", (LWT + rnd.randint(100, 400), "status_detector", "offline"))
db.execute("INSERT INTO eventos VALUES (?,?,?)", (RECONECTA + rnd.randint(250, 450), "status_detector", "online"))
ultimo_rec = 0
for seq, tp, n, l, c, ok in pubs:
    if not ok or tp < COLETOR:
        continue
    # TCP entrega em ordem: um atraso maior segura as mensagens seguintes
    rec = max(tp + atraso(), ultimo_rec + rnd.randint(1, 4))
    ultimo_rec = rec
    bruto = json.dumps({"id": "detector-01", "seq": seq, "t": tp, "v": n, "l": l, "c": int(c)}, separators=(",", ":"))
    db.execute("INSERT INTO leituras VALUES (?,?,?,?,?,?,?,?)", (rec, "detector-01", seq, tp, n, l, int(c), bruto))
db.execute("INSERT INTO eventos VALUES (?,?,?)", (FIM + 2000, "coletor_encerrado", ""))
db.commit()

# ---------- log serial (registrar_serial.py iniciado as 13:59) ----------
INICIO_LOG = ms(13, 59, 2, 410)
def carimbo(t):
    return datetime.fromtimestamp(t / 1000, TZ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
linhas = []
for (t, n, l, pot, c) in leituras_sensor:
    if t < INICIO_LOG:
        continue
    lat = t + rnd.randint(3, 12)
    linhas.append((lat, f"gas:{n}\tlimite:{l}\tpot:{pot}"))
linhas.append((RECONECTA - 20, "Conectando ao MQTT... conectado!"))
linhas.sort()
log = repo / "evidencias" / "serial_20261028_1359.log"
log.parent.mkdir(exist_ok=True)
n_leit = sum(1 for _, x in linhas if x.startswith("gas:"))
fim_log = linhas[-1][0]
dur = (fim_log - INICIO_LOG) / 1000
esper = int(dur / 0.5)
with open(log, "w", encoding="utf-8") as f:
    f.write("# DADOS SIMULADOS: gerados por ferramentas/simular_ensaios.py a partir dos parametros do prototipo (Secao 5.4 do paper).\n")
    for t, x in linhas:
        f.write(f"{carimbo(t)}  {x}\n")
    f.write("\nResumo do registro serial\n"
            f"  Arquivo:                ../evidencias/{log.name}\n"
            f"  Duracao:                {dur / 60:.1f} min\n"
            f"  Leituras registradas:   {n_leit}\n"
            f"  Leituras esperadas:     {esper} (1 a cada 0.5 s)\n"
            f"  Aproveitamento:         {100 * n_leit / esper:.1f}%\n"
            f"  Reinicios da placa:     0\n"
            f"  Conexoes ao MQTT:       1\n"
            f"  Falhas de conexao MQTT: 0\n")

# ---------- numeros para o paper ----------
def deteccao(e):
    for (t, n, l, pot, c) in leituras_sensor:
        if t >= e["t0"] and c:
            return (t - e["t0"]) / 1000
    return None
ar = [x for x in leituras_sensor if ms(14, 0) <= x[0] < ms(15, 0)]
serial_1h = sum(1 for t, x in linhas if x.startswith("gas:") and ms(14, 0) <= t < ms(15, 0))
res = {
    "serial_1h": serial_1h,
    "falsos_alertas_1h": sum(1 for i in range(1, len(ar)) if ar[i][4] and not ar[i - 1][4]),
    "det_gas": [round(deteccao(e), 2) for e in expos if e["tipo"] == "gas"],
    "det_fumaca": [round(deteccao(e), 2) for e in expos if e["tipo"] == "fumaca"],
    "det_sem_wifi": deteccao(expos[20]),
    "lwt_s": (LWT - WIFI_OFF) / 1000,
    "reconexao_s": (RECONECTA - WIFI_ON) / 1000,
}
print("Banco:", db_path)
print("Registro serial:", log)
print(json.dumps(res, indent=1))
