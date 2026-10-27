/*
 * Projeto: Detector de Gas com Dashboard Web + MQTT/EMQX (acesso de qualquer lugar)
 * Placa:   ESP32C3 Super Mini
 *
 * Dashboard local (mesma rede Wi-Fi):
 *   http://detector-gas.local   ou   http://<IP mostrado no monitor serial>
 *
 * Dashboard remoto (qualquer lugar):
 *   docs/index.html (publicado no GitHub Pages), conectado ao mesmo broker MQTT
 *
 * Biblioteca necessaria (Gerenciador de Bibliotecas da Arduino IDE):
 *   PubSubClient  (autor: Nick O'Leary)
 *
 * Senhas e usuarios ficam no arquivo secrets.h (fora do git).
 * Copie secrets.example.h para secrets.h e preencha.
 *
 * O potenciometro ajusta o LIMITE do nivel de gas:
 *   limite mais baixo  = detector mais sensivel (dispara com menos gas)
 *   limite mais alto   = detector menos sensivel
 *
 * A leitura do sensor e o alerta rodam numa tarefa separada, entao o
 * detector continua funcionando mesmo se o Wi-Fi ou a internet cairem.
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <PubSubClient.h>
#include <time.h>
#include <sys/time.h>

#include "secrets.h"   // WIFI_SSID, WIFI_SENHA, MQTT_USUARIO, MQTT_SENHA (nao vai para o git)


// === CONFIGURACAO DO WI-FI ====================

// Nome para acessar como http://<NOME_MDNS>.local
#define NOME_MDNS           "detector-gas"

// Tempo maximo esperando o Wi-Fi conectar ao ligar (ms)
#define TEMPO_MAX_WIFI      15000

// Descomente se a placa nao conectar no Wi-Fi (antena fraca de algumas Super Mini)
// #define WIFI_POTENCIA_REDUZIDA

// ==============================================


// === CONFIGURACAO DO MQTT (EMQX Cloud Serverless) =

// Endereco do deployment (campo "Address" na pagina Overview do EMQX Cloud)
#define MQTT_HOST           "z2d90268.ala.us-east-1.emqxsl.com"
#define MQTT_PORTA          8883

// Usuario e senha do ESP32 ficam no secrets.h

// Identificacao deste detector nas mensagens (campo "id")
#define ID_DISPOSITIVO      "detector-01"

// Prefixo dos topicos. Precisa ser igual ao do docs/index.html
#define MQTT_TOPICO_BASE    "detector-gas"

// De quanto em quanto tempo a leitura atual e enviada para a nuvem (ms).
// Alem disso, toda mudanca de estado (normal <-> critico) e enviada na hora.
// O plano gratis do EMQX tem 1 GB de trafego por mes: com 1000 ms o detector
// gasta uns 250 MB/mes. Com 500 ms passa de 400 MB; abaixo disso nao recomendo.
#define INTERVALO_PUBLICACAO_MQTT  1000

// De quanto em quanto tempo a lista de leituras e reenviada (ms)
// (serve para o dashboard remoto ja abrir com a lista preenchida)
#define INTERVALO_HISTORICO_MQTT   60000

// Tempo entre tentativas de reconexao ao broker (ms)
#define INTERVALO_RECONEXAO_MQTT   10000

// Descomente SO para teste, se a conexao falhar por causa do certificado.
// A conexao continua criptografada, mas sem confirmar que o servidor e o EMQX.
// #define MQTT_SEM_VERIFICAR_CERTIFICADO

// ==============================================


// === PORTAS ===================================
// Entradas analogicas precisam ficar entre GPIO0 e GPIO4 (ADC1),
// porque o ADC2 (GPIO5) nao funciona com o Wi-Fi ligado.

#define PORTA_SENSOR         3   // AO do MQ2 (passando pelo divisor de tensao)
#define PORTA_POTENCIOMETRO  4   // pino do meio do potenciometro
#define PORTA_ALERTA         5   // buzzer ou LED vermelho
#define PORTA_LED_VERDE      6   // LED verde

// ==============================================


// === AJUSTES DO LIMITE (POTENCIOMETRO) ========

// Faixa do limite que o potenciometro consegue ajustar
#define LIMITE_MINIMO        300    // potenciometro todo para um lado
#define LIMITE_MAXIMO        3500   // potenciometro todo para o outro lado

// Troque para 1 se quiser que o giro funcione ao contrario
#define INVERTER_POT         0

// Calibracao do potenciometro: leitura nas pontas do giro.
// Olhe o "pot:" no monitor serial com o potenciometro todo para cada lado
// e coloque os valores aqui se o ajuste nao estiver usando o giro todo.
#define POT_LEITURA_MINIMA   0
#define POT_LEITURA_MAXIMA   4095

// ==============================================


// === AJUSTES DA LEITURA =======================

// Intervalo em milissegundos entre as leituras
#define INTERVALO_LEITURAS   500

// Quantas leituras sao feitas e tiradas a media (reduz o "tremido" do ADC)
#define AMOSTRAS_MEDIA       16

// Margem para desligar o alerta: so desliga quando o gas cair
// HISTERESE pontos abaixo do limite. Use 0 para desativar.
#define HISTERESE            50

// Quantidade de leituras guardadas para a lista dos dashboards
#define TAMANHO_HISTORICO    60

// ==============================================


// === TOPICOS MQTT (montados a partir do prefixo) =

#define TOPICO_LEITURA      MQTT_TOPICO_BASE "/leitura"
#define TOPICO_HISTORICO    MQTT_TOPICO_BASE "/historico"
#define TOPICO_STATUS       MQTT_TOPICO_BASE "/status"

// ==============================================


// === CERTIFICADO RAIZ (DigiCert Global Root G2, usado pelo EMQX Cloud Serverless) =
// Se a conexao falhar com codigo -2, baixe o certificado na pagina Overview do
// deployment (arquivo emqxsl-ca.crt), abra no Bloco de Notas e cole o conteudo
// aqui no lugar deste, mantendo as linhas BEGIN e END.

static const char CERTIFICADO_RAIZ[] = R"CERT(
-----BEGIN CERTIFICATE-----
MIIDjjCCAnagAwIBAgIQAzrx5qcRqaC7KGSxHQn65TANBgkqhkiG9w0BAQsFADBh
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBH
MjAeFw0xMzA4MDExMjAwMDBaFw0zODAxMTUxMjAwMDBaMGExCzAJBgNVBAYTAlVT
MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5j
b20xIDAeBgNVBAMTF0RpZ2lDZXJ0IEdsb2JhbCBSb290IEcyMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuzfNNNx7a8myaJCtSnX/RrohCgiN9RlUyfuI
2/Ou8jqJkTx65qsGGmvPrC3oXgkkRLpimn7Wo6h+4FR1IAWsULecYxpsMNzaHxmx
1x7e/dfgy5SDN67sH0NO3Xss0r0upS/kqbitOtSZpLYl6ZtrAGCSYP9PIUkY92eQ
q2EGnI/yuum06ZIya7XzV+hdG82MHauVBJVJ8zUtluNJbd134/tJS7SsVQepj5Wz
tCO7TG1F8PapspUwtP1MVYwnSlcUfIKdzXOS0xZKBgyMUNGPHgm+F6HmIcr9g+UQ
vIOlCsRnKPZzFBQ9RnbDhxSJITRNrw9FDKZJobq7nMWxM4MphQIDAQABo0IwQDAP
BgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBhjAdBgNVHQ4EFgQUTiJUIBiV
5uNu5g/6+rkS7QYXjzkwDQYJKoZIhvcNAQELBQADggEBAGBnKJRvDkhj6zHd6mcY
1Yl9PMWLSn/pvtsrF9+wX3N3KjITOYFnQoQj8kVnNeyIv/iPsGEMNKSuIEyExtv4
NeF22d+mQrvHRAiGfzZ0JFrabA0UWTW98kndth/Jsw1HKj2ZL7tcu7XUIOGZX1NG
Fdtom/DzMNU+MeKNhJ7jitralj41E6Vf8PlwUHBHQRFXGU7Aj64GxJUTFy8bJZ91
8rGOmaFvE7FBcf6IKshPECBV1/MUReXgRPTqh5Uykw7+U0b6LJ3/iyK5S9kJRaTe
pLiaWN0bfVKfjllDiIGknibVb63dDcY3fe0Dkhvld1927jyNxF1WW6LZZm6zNTfl
MrY=
-----END CERTIFICATE-----
)CERT";

// ==============================================


// === VARIAVEIS GLOBAIS ========================

WebServer         servidor(80);
WiFiClientSecure  clienteSeguro;
PubSubClient      mqtt(clienteSeguro);

// Protege os dados compartilhados entre a tarefa do sensor e o resto do programa
SemaphoreHandle_t mutexDados;

uint16_t historicoValores[TAMANHO_HISTORICO];
uint16_t historicoLimites[TAMANHO_HISTORICO];
uint32_t historicoTempos[TAMANHO_HISTORICO];   // millis() de cada leitura
bool     historicoCritico[TAMANHO_HISTORICO];
uint8_t  indiceHistorico = 0;
uint8_t  totalHistorico  = 0;

volatile uint16_t nivelAtual   = 0;
volatile uint16_t limiteAtual  = LIMITE_MINIMO;
volatile uint16_t leituraPot   = 0;
volatile bool     nivelCritico = false;

bool horaSincronizada = false;
unsigned long ultimaTentativaMqtt = 0;
unsigned long ultimoHistoricoMqtt = 0;
unsigned long ultimaPublicacaoMqtt = 0;

// Numero sequencial de cada mensagem de leitura (volta a 0 quando a placa reinicia).
// Permite contar mensagens perdidas: lacunas no seq = mensagens que nao chegaram.
uint32_t seqLeitura = 0;
bool     estadoPublicado = false;   // ultimo estado enviado (para mandar mudancas na hora)

// ==============================================


// === PAGINA DO DASHBOARD LOCAL ================

const char PAGINA[] = R"rawliteral(
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Detector de Gás</title>
<style>
  :root{
    --fundo:#e9edf1; --painel:#ffffff; --texto:#1d2733; --suave:#5d6b7a;
    --seguro:#1f8a4c; --perigo:#c4291c; --trilho:#d3dae2; --linha:#c9d1da;
  }
  @media (prefers-color-scheme: dark){
    :root{
      --fundo:#141a20; --painel:#1e262e; --texto:#e6ebf0; --suave:#93a1b0;
      --seguro:#3fbf73; --perigo:#ff5a4a; --trilho:#2d3742; --linha:#2d3742;
    }
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
       background:var(--fundo);color:var(--texto)}
  main{max-width:560px;margin:0 auto;padding:20px 16px 40px}
  h1{font-size:1.25rem;margin:0 0 16px}
  .painel{background:var(--painel);border-radius:10px;padding:20px;margin-bottom:16px}
  .leitura{display:flex;align-items:baseline;justify-content:space-between;gap:12px}
  #valor{font-size:3.5rem;font-weight:700;font-variant-numeric:tabular-nums;line-height:1}
  #status{font-weight:600;font-size:1.05rem}
  .barra{position:relative;height:22px;background:var(--trilho);border-radius:11px;
         overflow:hidden;margin-top:18px}
  #preenche{height:100%;width:0;background:var(--seguro);transition:width .3s,background .3s}
  #limite{position:absolute;top:0;bottom:0;width:3px;background:var(--texto);opacity:.6;
          transition:left .3s}
  .escala{display:flex;justify-content:space-between;color:var(--suave);
          font-size:.8rem;margin-top:6px}
  #txtLimite{color:var(--texto);font-weight:600}
  h2{font-size:1rem;margin:0 0 10px}
  .tabela{max-height:50vh;overflow-y:auto}
  table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
  th,td{text-align:left;padding:7px 4px;border-bottom:1px solid var(--linha)}
  th{color:var(--suave);font-weight:500;font-size:.85rem;position:sticky;top:0;background:var(--painel)}
  td.alto{color:var(--perigo);font-weight:700}
</style>
</head>
<body>
<main>
  <h1>Detector de gás</h1>

  <section class="painel">
    <div class="leitura">
      <div id="valor">--</div>
      <div id="status">Conectando…</div>
    </div>
    <div class="barra"><div id="preenche"></div><div id="limite"></div></div>
    <div class="escala"><span>0</span><span id="txtLimite">Limite</span><span>4095</span></div>
  </section>

  <section class="painel">
    <h2>Últimas leituras</h2>
    <div class="tabela">
      <table>
        <thead><tr><th>Hora</th><th>Nível</th><th>Limite</th></tr></thead>
        <tbody id="lista"></tbody>
      </table>
    </div>
  </section>
</main>

<script>
const $ = id => document.getElementById(id);

async function atualizar(){
  try{
    const r = await fetch('/dados');
    const d = await r.json();

    $('valor').textContent = d.atual;
    $('status').textContent = d.critico ? 'Nível crítico' : 'Normal';
    $('status').style.color = d.critico ? 'var(--perigo)' : 'var(--seguro)';

    $('preenche').style.width = (d.atual / 4095 * 100) + '%';
    $('preenche').style.background = d.critico ? 'var(--perigo)' : 'var(--seguro)';
    $('limite').style.left = (d.limite / 4095 * 100) + '%';
    $('txtLimite').textContent = 'Limite ' + d.limite;

    const agora = Date.now();
    $('lista').innerHTML = d.historico.map(([t, v, l, c]) => {
      const hora = new Date(agora - (d.agora - t)).toLocaleTimeString('pt-BR');
      return '<tr><td>' + hora + '</td><td class="' + (c ? 'alto' : '') + '">' + v +
             '</td><td>' + l + '</td></tr>';
    }).join('');
  }catch(e){
    $('status').textContent = 'Sem resposta do ESP32. Verifique o Wi-Fi.';
    $('status').style.color = 'var(--suave)';
  }
}

setInterval(atualizar, 500);
atualizar();
</script>
</body>
</html>
)rawliteral";

// ==============================================


// === FUNCOES DO SENSOR ========================

// Le uma porta analogica varias vezes e devolve a media
uint16_t lerMedia(uint8_t porta) {
    uint32_t soma = 0;
    for (uint8_t i = 0; i < AMOSTRAS_MEDIA; i++) {
        soma += analogRead(porta);
    }
    return soma / AMOSTRAS_MEDIA;
}

// Le o potenciometro e converte para um valor de limite
uint16_t lerLimite() {
    leituraPot = lerMedia(PORTA_POTENCIOMETRO);

    long pot = constrain((long)leituraPot, (long)POT_LEITURA_MINIMA, (long)POT_LEITURA_MAXIMA);
    if (INVERTER_POT) {
        pot = POT_LEITURA_MINIMA + POT_LEITURA_MAXIMA - pot;
    }

    return map(pot, POT_LEITURA_MINIMA, POT_LEITURA_MAXIMA, LIMITE_MINIMO, LIMITE_MAXIMO);
}

// Le o sensor e o potenciometro, aciona as saidas e guarda no historico
void lerSensor() {
    uint16_t nivel  = lerMedia(PORTA_SENSOR);
    uint16_t limite = lerLimite();
    bool critico    = nivelCritico;

    // Liga o alerta acima do limite; so desliga quando cair abaixo de (limite - HISTERESE)
    if (!critico && nivel > limite) {
        critico = true;
    } 
    else if (critico && nivel + HISTERESE < limite) {
        critico = false;
    }

    digitalWrite(PORTA_ALERTA, critico);
    digitalWrite(PORTA_LED_VERDE, !critico);

    xSemaphoreTake(mutexDados, portMAX_DELAY);
    nivelAtual   = nivel;
    limiteAtual  = limite;
    nivelCritico = critico;

    historicoValores[indiceHistorico] = nivel;
    historicoLimites[indiceHistorico] = limite;
    historicoTempos[indiceHistorico]  = millis();
    historicoCritico[indiceHistorico] = critico;
    indiceHistorico = (indiceHistorico + 1) % TAMANHO_HISTORICO;

    if (totalHistorico < TAMANHO_HISTORICO) totalHistorico++;

    xSemaphoreGive(mutexDados);

    // Formato compativel com o Plotter Serial da Arduino IDE
    Serial.printf("gas:%u\tlimite:%u\tpot:%u\n", nivel, limite, (uint16_t)leituraPot);
}

// Tarefa que roda sozinha, independente do Wi-Fi e do MQTT
void tarefaSensor(void* parametro) {
    TickType_t ultimoDespertar = xTaskGetTickCount();
    while(1) {
        lerSensor();
        vTaskDelayUntil(&ultimoDespertar, pdMS_TO_TICKS(INTERVALO_LEITURAS));
    }
}

// ==============================================


// === FUNCOES DO DASHBOARD LOCAL ===============

void enviarPagina() {
    servidor.send(200, "text/html; charset=utf-8", PAGINA);
}

// Envia os dados em JSON (leitura mais recente primeiro)
void enviarDados() {
    String json;
    json.reserve(96 + TAMANHO_HISTORICO * 28);

    xSemaphoreTake(mutexDados, portMAX_DELAY);
    json = "{\"atual\":"   + String(nivelAtual) +
           ",\"limite\":"  + String(limiteAtual) +
           ",\"critico\":" + String(nivelCritico ? "true" : "false") +
           ",\"agora\":"   + String(millis()) +
           ",\"historico\":[";

    for (uint8_t i = 0; i < totalHistorico; i++) {
        uint8_t pos = (indiceHistorico + TAMANHO_HISTORICO - 1 - i) % TAMANHO_HISTORICO;
        if (i > 0) json += ",";
        json += "[" + String(historicoTempos[pos]) +
                "," + String(historicoValores[pos]) +
                "," + String(historicoLimites[pos]) +
                "," + String(historicoCritico[pos] ? 1 : 0) + "]";
    }
    xSemaphoreGive(mutexDados);

    json += "]}";
    servidor.send(200, "application/json", json);
}

// ==============================================


// === FUNCOES DO MQTT ==========================

// Hora atual em milissegundos desde 1970 (vem da internet via NTP)
uint64_t agoraEpochMs() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (uint64_t)tv.tv_sec * 1000ULL + tv.tv_usec / 1000;
}

// Publica a leitura mais recente (retida: quem abrir o dashboard recebe na hora)
void publicarLeitura() {
    xSemaphoreTake(mutexDados, portMAX_DELAY);
    uint16_t v = nivelAtual;
    uint16_t l = limiteAtual;
    bool     c = nivelCritico;
    xSemaphoreGive(mutexDados);

    // id = detector, seq = numero da mensagem, t = hora (ms desde 1970, UTC),
    // v = nivel de gas (ADC), l = limite, c = 1 se critico
    char msg[160];
    snprintf(msg, sizeof(msg),
             "{\"id\":\"%s\",\"seq\":%lu,\"t\":%llu,\"v\":%u,\"l\":%u,\"c\":%d}",
             ID_DISPOSITIVO, (unsigned long)seqLeitura, (unsigned long long)agoraEpochMs(),
             v, l, c ? 1 : 0);
    if (mqtt.publish(TOPICO_LEITURA, msg, true)) {
        estadoPublicado = c;
    }
    seqLeitura++;   // conta toda tentativa: envio que falhou aparece como lacuna no seq
}

// Publica a lista das ultimas leituras (mais recente primeiro)
void publicarHistorico() {
    String json;
    json.reserve(16 + TAMANHO_HISTORICO * 32);
    json = "{\"h\":[";

    char item[48];
    uint64_t agoraMs     = agoraEpochMs();
    uint32_t agoraMillis = millis();

    xSemaphoreTake(mutexDados, portMAX_DELAY);
    for (uint8_t i = 0; i < totalHistorico; i++) {
        uint8_t pos = (indiceHistorico + TAMANHO_HISTORICO - 1 - i) % TAMANHO_HISTORICO;
        uint64_t t  = agoraMs - (uint32_t)(agoraMillis - historicoTempos[pos]);
        snprintf(item, sizeof(item), "%s[%llu,%u,%u,%d]", i > 0 ? "," : "",
                 (unsigned long long)t, historicoValores[pos], historicoLimites[pos],
                 historicoCritico[pos] ? 1 : 0);
        json += item;
    }
    xSemaphoreGive(mutexDados);

    json += "]}";
    mqtt.publish(TOPICO_HISTORICO, json.c_str(), true);
}

// Conecta ao broker. Se o ESP32 cair, o broker publica "offline" sozinho.
void conectarMqtt() {
    String idCliente = "detector-gas-" + String((uint32_t)ESP.getEfuseMac(), HEX);

    Serial.print("Conectando ao MQTT... ");
    if (mqtt.connect(idCliente.c_str(), MQTT_USUARIO, MQTT_SENHA,
                     TOPICO_STATUS, 1, true, "offline")) {
        Serial.println("conectado!");
        mqtt.publish(TOPICO_STATUS, "online", true);
        publicarHistorico();
        ultimoHistoricoMqtt = millis();
    } 
    else {
        // Codigos: -4 tempo esgotado, -2 falha de rede/certificado, 4 usuario ou senha errados, 5 nao autorizado
        Serial.printf(
            "falhou (codigo %d). Nova tentativa em %d s\n",
            mqtt.state(), 
            (INTERVALO_RECONEXAO_MQTT / 1000)
        );
    }
}

// ==============================================


// === SETUP E LOOP =============================

void setup() {
    pinMode(PORTA_ALERTA, OUTPUT);
    pinMode(PORTA_LED_VERDE, OUTPUT);
    analogReadResolution(12);   // leituras de 0 a 4095

    Serial.begin(115200);

    // Inicia a tarefa do sensor ANTES do Wi-Fi: o detector funciona desde o primeiro segundo
    mutexDados = xSemaphoreCreateMutex();
    xTaskCreate(tarefaSensor, "sensor", 4096, NULL, 2, NULL);

    // Conecta ao Wi-Fi
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_SENHA);
#ifdef WIFI_POTENCIA_REDUZIDA
    WiFi.setTxPower(WIFI_POWER_8_5dBm);
#endif

    Serial.println("Conectando ao Wi-Fi...");
    unsigned long inicio = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - inicio < TEMPO_MAX_WIFI) {
        delay(250);
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.print("Dashboard local em: http://");
        Serial.println(WiFi.localIP());
        if (MDNS.begin(NOME_MDNS)) {
            Serial.println("Ou em: http://" NOME_MDNS ".local");
        }
    } 
    else {
        Serial.println("Nao conectou ainda. O ESP32 vai continuar tentando sozinho.");
    }

    // Pede a hora certa para a internet (necessaria para o certificado e para os horarios)
    configTime(0, 0, "pool.ntp.org", "time.google.com");

    // Dashboard local
    servidor.on("/", enviarPagina);
    servidor.on("/dados", enviarDados);
    servidor.begin();

    // MQTT com conexao segura (TLS)
#ifdef MQTT_SEM_VERIFICAR_CERTIFICADO
    clienteSeguro.setInsecure();
#else
    clienteSeguro.setCACert(CERTIFICADO_RAIZ);
#endif
    mqtt.setServer(MQTT_HOST, MQTT_PORTA);
    mqtt.setBufferSize(3072);    // espaco para a lista de leituras
    mqtt.setKeepAlive(30);
    mqtt.setSocketTimeout(10);

    ultimaTentativaMqtt = millis() - INTERVALO_RECONEXAO_MQTT;   // tenta logo de cara
}

void loop() {
    // Atende quem abrir o dashboard local
    servidor.handleClient();

    // Espera a hora chegar da internet antes de usar o MQTT
    if (!horaSincronizada && time(nullptr) > 1700000000) {
        horaSincronizada = true;
        Serial.println("Hora sincronizada.");
    }

    if (WiFi.status() == WL_CONNECTED && horaSincronizada) {
        if (!mqtt.connected()) {
            if (millis() - ultimaTentativaMqtt >= INTERVALO_RECONEXAO_MQTT) {
                ultimaTentativaMqtt = millis();
                conectarMqtt();
            }
        } 
        else {
            mqtt.loop();

            // Envia no intervalo normal OU imediatamente quando o estado muda
            unsigned long desdeUltimo = millis() - ultimaPublicacaoMqtt;
            if (desdeUltimo >= INTERVALO_PUBLICACAO_MQTT ||
                (nivelCritico != estadoPublicado && desdeUltimo >= 100)) {
                ultimaPublicacaoMqtt = millis();
                publicarLeitura();
            }

            if (millis() - ultimoHistoricoMqtt >= INTERVALO_HISTORICO_MQTT) {
                ultimoHistoricoMqtt = millis();
                publicarHistorico();
            }
        }
    }

    delay(2);   // da folga para as outras tarefas
}

// ==============================================
