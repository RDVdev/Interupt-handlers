
#include <SPI.h>
#include <LoRa.h>
#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>

// ==== PIN CONFIGURATION ====
#define LORA_SS      10
#define LORA_RST     9
#define LORA_DIO0    2
#define LORA_DIO1    3   // Optional

// ==== WiFi Config ====
const char* WIFI_SSID = "TP-Link_14E9";
const char* WIFI_PASS = "08642592";

// ==== Server Config ====
const char* SERVER = "10.2.36.181";   // Server IP
const int SERVER_PORT = 8000;
const char* DEVICE_ID = "RX002";      // Device ID for endpoint

WiFiClient wifiClient;
HttpClient client(wifiClient, SERVER, SERVER_PORT);

const char* TEAM_ID = "skywalker"; // Filter messages starting with this

void setup() {
  Serial.begin(115200);
  // while (!Serial); 

  Serial.println("\n=== Initializing LoRa Receiver (Internal LED Mode) ===");

  // Initialize Internal LED
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW); // Start OFF

  // 1. Connect to WiFi
  connectToWiFi();

  // 2. Setup LoRa
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(868E6)) { // 868MHz
    Serial.println("❌ LoRa init failed! Check wiring.");
    while (1);
  }

  // Configure LoRa parameters to match Transmitter
  LoRa.setSyncWord(0xAB);
  LoRa.setSpreadingFactor(12);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(8);

  Serial.println("✅ LoRa Receiver ready! Waiting for packets...");
}

void loop() {
  // Check if WiFi is still connected
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_BUILTIN, LOW); // Turn OFF LED if WiFi is lost
    Serial.println("⚠ WiFi lost! Reconnecting...");
    connectToWiFi();
  }

  int packetSize = LoRa.parsePacket();

  if (packetSize) {
    String message = "";
    while (LoRa.available()) {
      message += (char)LoRa.read();
    }

    int rssi = LoRa.packetRssi();

    // Verify Team ID
    if (message.startsWith(TEAM_ID)) {
      // Extract SEQ number
      int seqIndex = message.indexOf("SEQ:");
      if (seqIndex != -1) {
        String seqStr = message.substring(seqIndex + 4);
        seqStr.trim();
        int seqNum = seqStr.toInt();

        Serial.print("➡ Processing Packet SEQ: ");
        Serial.print(seqNum);
        Serial.print(" | RSSI: ");
        Serial.println(rssi);

        // Upload to Server
        uploadRSSI(seqNum, rssi);
      }
    }
  }
}

// ----- Connect to WiFi -----
void connectToWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);

  while (WiFi.begin(WIFI_SSID, WIFI_PASS) != WL_CONNECTED) {
    Serial.print(".");
    digitalWrite(LED_BUILTIN, LOW); // LED OFF while trying to connect
    delay(1000);
  }

  Serial.println("\n✅ Connected to WiFi!");
  Serial.print("Local IP: ");
  Serial.println(WiFi.localIP());

  // Turn ON LED (Solid) to indicate WiFi is Connected
  digitalWrite(LED_BUILTIN, HIGH);
}

// ----- Upload RSSI to Flask server -----
void uploadRSSI(int seq, int rssi) {
  String endpoint = String("/") + DEVICE_ID + "/data";
  
  String payload = String("{\"message\":\"skywalker\",\"seq\":") + String(seq) +
                   String(",\"rssi\":") + String(rssi) + "}";

  client.beginRequest();
  client.post(endpoint);
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Length", payload.length());
  client.beginBody();
  client.print(payload);
  client.endRequest();

  int statusCode = client.responseStatusCode();
  String response = client.responseBody();

  if (statusCode == 200 || statusCode == 201) {
    Serial.println(" ✅ Server Accepted");
    
    // VISUAL FEEDBACK: "Wink" the LED
    // Briefly turn OFF and then back ON to show activity
    digitalWrite(LED_BUILTIN, LOW);
    delay(150); 
    digitalWrite(LED_BUILTIN, HIGH);
    
  } else {
    Serial.print(" ❌ Server Error: ");
    Serial.println(statusCode);
  }
}