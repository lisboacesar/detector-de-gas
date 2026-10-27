# Evidências dos testes

Esta pasta guarda os registros que comprovam os resultados do paper (Tabela 11).
As ferramentas da pasta `ferramentas/` salvam aqui automaticamente.

| Arquivo | Gerado por | Teste |
| --- | --- | --- |
| `serial_<data>.log` | `registrar_serial.py` | 1. Uma hora em ar limpo (leituras e reinícios) |
| `teste1_ar_limpo/` | `relatorio.py --ultimos 60 --nome teste1_ar_limpo` | 1. Taxa de entrega, falsos alertas |
| `teste2_exposicoes/` | `relatorio.py --nome teste2_exposicoes --inicio ... --fim ...` | 2. Alertas e gráfico (Figura 7) |
| `teste5_autonomia/` | `relatorio.py --nome teste5_autonomia --inicio ... --fim ...` | 5. Queda e reconexão |
| `teste_seguranca_<data>.txt` | `teste_seguranca.py` | 4. Segurança do broker |
| `prints/` | manual | prints do aplicativo web, do EMQX e dos terminais |
| `videos/` | manual | vídeo curto do alarme (LED e buzzer com cronômetro) |

Cada pasta de relatório contém `relatorio.md`, `leituras.csv`, `eventos.csv` e `grafico.png`.
