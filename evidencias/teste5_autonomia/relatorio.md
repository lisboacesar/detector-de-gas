> DADOS SIMULADOS: gerados por ferramentas/simular_ensaios.py a partir dos parametros do prototipo e processados pelo relatorio.py (Secao 5.4 do paper).

# Relatório do detector de gás: teste5_autonomia

Período: 28/10/2026 16:05:00 a 28/10/2026 16:15:59 (11,0 min)

## Transmissão e armazenamento

| Métrica | Valor |
| --- | --- |
| Mensagens gravadas no banco | 464 |
| Mensagens esperadas pelo seq | 486 |
| Taxa de entrega pelo seq | 95,5% |
| Mensagens esperadas pelo tempo (1 a cada 1 s) | 659 |
| Cobertura pelo tempo | 70,4% |
| Lacunas no seq | 5 (total de 22 mensagens) |
| Mensagens duplicadas | 0 |
| Reinícios da placa (seq voltou a 0) | 0 |

## Atraso entre a leitura no ESP32 e a chegada ao coletor

Depende dos relógios do ESP32 (NTP) e do computador estarem sincronizados.

| Métrica | Valor |
| --- | --- |
| Médio | 0,37 s |
| Mediana | 0,34 s |
| 95% das mensagens abaixo de | 0,68 s |
| Máximo | 1,69 s |

## Leituras do sensor

| Métrica | Valor |
| --- | --- |
| Nível mínimo / médio / máximo | 1427 / 1567 / 3616 |
| Limite(s) usado(s) | 2096, 2097, 2098, 2099, 2100, 2101, 2102, 2103, 2104, 2105, 2106, 2107, 2110 |
| Episódios de alerta | 1 |

| # | Início | Fim | Duração | Pico | Limite |
| --- | --- | --- | --- | --- | --- |
| 1 | 28/10/2026 16:13:00 | 28/10/2026 16:13:32 | 32,03 s | 3616 | 2104 |

## Quedas e reconexões do detector (tópico de status)

| # | Ficou offline | Voltou online | Tempo fora |
| --- | --- | --- | --- |
| 1 | 28/10/2026 16:08:45 | 28/10/2026 16:11:09 | 144,33 s |

## Lacunas no seq

| Depois de | Seq anterior | Seq seguinte | Mensagens faltando |
| --- | --- | --- | --- |
| 28/10/2026 16:06:39 | 7746 | 7751 | 4 |
| 28/10/2026 16:07:59 | 7826 | 7842 | 15 |
| 28/10/2026 16:13:27 | 7981 | 7983 | 1 |
| 28/10/2026 16:14:33 | 8047 | 8049 | 1 |
| 28/10/2026 16:14:42 | 8056 | 8058 | 1 |

Arquivos: leituras.csv, eventos.csv, grafico.png
