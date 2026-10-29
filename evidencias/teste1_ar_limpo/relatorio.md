> DADOS PROVISORIOS: gerados por simulacao para montar o paper antes dos ensaios. Substituir pelo registro real antes da entrega.

# Relatório do detector de gás: teste1_ar_limpo

Período: 28/10/2026 14:00:00 a 28/10/2026 14:59:59 (60,0 min)

## Transmissão e armazenamento

| Métrica | Valor |
| --- | --- |
| Mensagens gravadas no banco | 3539 |
| Mensagens esperadas pelo seq | 3589 |
| Taxa de entrega pelo seq | 98,6% |
| Mensagens esperadas pelo tempo (1 a cada 1 s) | 3599 |
| Cobertura pelo tempo | 98,3% |
| Lacunas no seq | 30 (total de 50 mensagens) |
| Mensagens duplicadas | 0 |
| Reinícios da placa (seq voltou a 0) | 0 |

## Atraso entre a leitura no ESP32 e a chegada ao coletor

Depende dos relógios do ESP32 (NTP) e do computador estarem sincronizados.

| Métrica | Valor |
| --- | --- |
| Médio | 0,37 s |
| Mediana | 0,33 s |
| 95% das mensagens abaixo de | 0,68 s |
| Máximo | 2,23 s |

## Leituras do sensor

| Métrica | Valor |
| --- | --- |
| Nível mínimo / médio / máximo | 1409 / 1439 / 1466 |
| Limite(s) usado(s) | 2093, 2094, 2095, 2096, 2097, 2098, 2099, 2100, 2101, 2102, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2111 |
| Episódios de alerta | 0 |

## Quedas e reconexões do detector (tópico de status)

Nenhuma queda registrada no período.

## Lacunas no seq

| Depois de | Seq anterior | Seq seguinte | Mensagens faltando |
| --- | --- | --- | --- |
| 28/10/2026 14:00:09 | 139 | 142 | 2 |
| 28/10/2026 14:00:26 | 156 | 158 | 1 |
| 28/10/2026 14:00:58 | 188 | 191 | 2 |
| 28/10/2026 14:01:27 | 217 | 219 | 1 |
| 28/10/2026 14:04:29 | 398 | 400 | 1 |
| 28/10/2026 14:05:22 | 451 | 455 | 3 |
| 28/10/2026 14:05:44 | 473 | 475 | 1 |
| 28/10/2026 14:06:29 | 518 | 520 | 1 |
| 28/10/2026 14:11:44 | 832 | 835 | 2 |
| 28/10/2026 14:12:33 | 881 | 883 | 1 |
| 28/10/2026 14:18:33 | 1240 | 1244 | 3 |
| 28/10/2026 14:18:46 | 1253 | 1256 | 2 |
| 28/10/2026 14:19:27 | 1294 | 1297 | 2 |
| 28/10/2026 14:22:46 | 1492 | 1494 | 1 |
| 28/10/2026 14:23:19 | 1525 | 1527 | 1 |
| 28/10/2026 14:26:55 | 1740 | 1745 | 4 |
| 28/10/2026 14:27:01 | 1746 | 1749 | 2 |
| 28/10/2026 14:28:04 | 1809 | 1811 | 1 |
| 28/10/2026 14:28:16 | 1821 | 1824 | 2 |
| 28/10/2026 14:30:07 | 1932 | 1935 | 2 |
| 28/10/2026 14:32:56 | 2100 | 2102 | 1 |
| 28/10/2026 14:33:42 | 2146 | 2148 | 1 |
| 28/10/2026 14:40:49 | 2572 | 2575 | 2 |
| 28/10/2026 14:42:44 | 2686 | 2688 | 1 |
| 28/10/2026 14:45:08 | 2830 | 2834 | 3 |
| 28/10/2026 14:47:24 | 2966 | 2968 | 1 |
| 28/10/2026 14:48:20 | 3022 | 3025 | 2 |
| 28/10/2026 14:48:30 | 3031 | 3033 | 1 |
| 28/10/2026 14:53:25 | 3326 | 3328 | 1 |
| 28/10/2026 14:53:28 | 3329 | 3332 | 2 |

Arquivos: leituras.csv, eventos.csv, grafico.png
