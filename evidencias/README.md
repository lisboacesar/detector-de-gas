# Evidências dos testes

> **Atenção: os arquivos desta versão são provisórios.** Foram gerados com dados simulados,
> no mesmo formato das ferramentas, para montar o paper antes dos ensaios. Os relatórios e os
> gráficos saíram do próprio `relatorio.py`, rodado sobre um banco simulado. Antes da entrega,
> rode os ensaios e substitua cada arquivo pelo registro real (os comandos abaixo sobrescrevem
> as mesmas pastas). As fotos e prints da pasta `prints/` são reais.

Esta pasta guarda os registros que comprovam os resultados do paper (Tabela 11).
As ferramentas da pasta `ferramentas/` salvam aqui automaticamente.

| Arquivo | Gerado por | Teste | Situação |
| --- | --- | --- | --- |
| `serial_<data>.log` | `registrar_serial.py` | 1. Uma hora em ar limpo (leituras e reinícios) | provisório |
| `teste1_ar_limpo/` | `relatorio.py --inicio ... --fim ... --nome teste1_ar_limpo` | 1. Taxa de entrega, atraso, falsos alertas | provisório |
| `teste2_exposicoes/` | `relatorio.py --nome teste2_exposicoes --inicio ... --fim ...` | 2. Alertas e gráfico (Figura 6 do paper) | provisório |
| `teste5_autonomia/` | `relatorio.py --nome teste5_autonomia --inicio ... --fim ...` | 5. Queda e reconexão | provisório |
| `teste_seguranca_<data>.txt` | `teste_seguranca.py` | 4. Segurança do broker | provisório |
| `custo_hardware.csv` | manual | Custo estimado do hardware (Tabela 7) | estimativa |
| `prints/` | manual | prints do aplicativo web, foto e montagem do protótipo | real |
| `videos/` | manual | vídeo curto do alarme (LED e buzzer com cronômetro) | falta gravar |

Cada pasta de relatório contém `relatorio.md`, `leituras.csv`, `eventos.csv` e `grafico.png`.

## Roteiro dos ensaios (o mesmo usado na simulação)

1. Deixar o sensor ligado antes (pré-aquecimento) e iniciar `python coletor.py` e `python registrar_serial.py COM5`.
2. Ar limpo: 1 hora sem gás. Relatório: `python relatorio.py --inicio "AAAA-MM-DD 14:00" --fim "AAAA-MM-DD 15:00" --nome teste1_ar_limpo`.
3. Exposições: 10 com gás de isqueiro (sem chama, a poucos centímetros) e 10 com fumaça de palito recém-apagado, esperando a leitura voltar à linha de base entre elas. Cronometrar o tempo até o alarme. Relatório com `--nome teste2_exposicoes`.
4. Segurança: `python teste_seguranca.py`.
5. Autonomia: desligar o Wi-Fi do roteador, aproximar o gás (o alarme deve tocar), religar o Wi-Fi e conferir no aplicativo o status offline e a reconexão. Relatório com `--nome teste5_autonomia`. Filmar o alarme.
