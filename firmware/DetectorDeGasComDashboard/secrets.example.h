/*
 * Modelo das credenciais do detector.
 *
 * 1. Copie este arquivo e renomeie a copia para secrets.h (na mesma pasta).
 * 2. Preencha os valores reais no secrets.h.
 * 3. O secrets.h esta no .gitignore e NUNCA deve ser enviado para o GitHub.
 */

#pragma once

// Rede Wi-Fi 2,4 GHz (o ESP32-C3 nao conecta em redes 5 GHz)
#define WIFI_SSID     "NOME_DA_REDE"
#define WIFI_SENHA    "SENHA_DA_REDE"

// Usuario do ESP32 no EMQX Cloud (Access Control > Authentication).
// Use um usuario diferente do usuario do dashboard.
#define MQTT_USUARIO  "esp32"
#define MQTT_SENHA    "SENHA_DA_ESP32"
