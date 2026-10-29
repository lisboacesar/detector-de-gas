# Evidências dos testes

Esta pasta guarda os registros que sustentam os resultados do paper (Tabela 11 e Figura 6).

**Os ensaios de desempenho foram reproduzidos por simulação** (Seção 5.4 do paper), alternativa
prevista no roteiro da disciplina. O programa `ferramentas/simular_ensaios.py` gera o banco do
coletor e o registro serial com a linha de base e o limite observados no protótipo, a mesma lógica
de limite e histerese do firmware e o envio a cada 1 s com perdas, atrasos e testamento (LWT).
Os relatórios e gráficos saíram do próprio `relatorio.py`. As fotos e prints da pasta `prints/`
são do protótipo real.

| Arquivo | Gerado por | Teste | Origem |
| --- | --- | --- | --- |
| `serial_20261028_1359.log` | `simular_ensaios.py` | 1. Uma hora em ar limpo (leituras e reinícios) | simulado |
| `teste1_ar_limpo/` | `relatorio.py --nome teste1_ar_limpo` | 1. Taxa de entrega, atraso, falsos alertas | simulado |
| `teste2_exposicoes/` | `relatorio.py --nome teste2_exposicoes` | 2. Alertas e gráfico (Figura 6 do paper) | simulado |
| `teste5_autonomia/` | `relatorio.py --nome teste5_autonomia` | 5. Queda e reconexão | simulado |
| `teste_seguranca_20261028_1622.txt` | resultado esperado do `teste_seguranca.py` | 4. Segurança do broker | simulado |
| `custo_hardware.csv` | levantamento de preços | Custo do hardware (Tabela 7) | real (preços de 29/10/2026) |
| `prints/` | manual | Aplicativo web, foto e montagem do protótipo | real |

Cada pasta de relatório contém `relatorio.md`, `leituras.csv`, `eventos.csv` e `grafico.png`.

## Como reproduzir

```bash
cd ferramentas
pip install -r requirements.txt
python simular_ensaios.py
python relatorio.py --inicio "2026-10-28 14:00" --fim "2026-10-28 15:00" --nome teste1_ar_limpo
python relatorio.py --inicio "2026-10-28 15:03" --fim "2026-10-28 16:02" --nome teste2_exposicoes
python relatorio.py --inicio "2026-10-28 16:05" --fim "2026-10-28 16:16" --nome teste5_autonomia
```

A semente é fixa, então os números saem iguais aos do paper (no fuso de São Luís, `TZ=America/Fortaleza`).

## Ensaios com o protótipo (trabalho futuro)

1. Deixar o sensor ligado antes (pré-aquecimento) e iniciar `python coletor.py` e `python registrar_serial.py COM5`.
2. Ar limpo: 1 hora sem gás. Relatório com `--nome teste1_ar_limpo`.
3. Exposições: 10 com gás de isqueiro (sem chama, a poucos centímetros) e 10 com fumaça de palito recém-apagado, esperando a leitura voltar à linha de base entre elas. Relatório com `--nome teste2_exposicoes`.
4. Segurança: `python teste_seguranca.py`.
5. Autonomia: desligar o Wi-Fi do roteador, aproximar o gás, religar o Wi-Fi e conferir no aplicativo o status offline e a reconexão. Relatório com `--nome teste5_autonomia`.
