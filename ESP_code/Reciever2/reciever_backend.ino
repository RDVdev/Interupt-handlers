#include <SPI.h>
#include <LoRa.h>
#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>

// ==== LoRa Pins ====
#define LORA_SS     10
#define LORA_RST    9
#define LORA_DIO0   2
#define LORA_DIO1   3   // Optional

// ==== WiFi Config ====
const char* WIFI_SSID = "OnePlus Nord CE3 5G";
const char* WIFI_PASS = "help@2326";

// ==== Server Config ====
const char* SERVER = "10.148.60.254";  // Flask server IP
const int SERVER_PORT = 5000;

WiFiClient wifiClient;
HttpClient client(wifiClient, SERVER, SERVER_PORT);

const char* TEAM_ID = "skywalker"; // For filtering LoRa messages

void setup() {
  Serial.begin(115200);
  while (!Serial);

  Serial.println("\n=== Initializing LoRa Receiver + WiFi ===");

  connectToWiFi();

  // ----- Setup LoRa -----
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(868E6)) {
    Serial.println("❌ LoRa init failed! Check wiring.");
    while (1);
  }

  LoRa.setSyncWord(0xAB);  // Must match transmitter
  LoRa.setSpreadingFactor(12);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(8);

  Serial.println("✅ LoRa Receiver ready! Waiting for packets...");
}

void loop() {
  int packetSize = LoRa.parsePacket();

  if (packetSize) {
    Serial.println("\n📩 Packet received!");

    String message = "";
    while (LoRa.available()) {
      message += (char)LoRa.read();
    }

    int rssi = LoRa.packetRssi();
    float snr = LoRa.packetSnr();

    Serial.print("Received LoRa message: ");
    Serial.println(message);
    Serial.print("RSSI: ");
    Serial.println(rssi);
    Serial.print("SNR: ");
    Serial.println(snr);

    // Only process messages from the team
    if (message.startsWith(TEAM_ID)) {
      // Extract SEQ number from message
      int seqIndex = message.indexOf("SEQ:");
      int seqNum = -1;
      if (seqIndex != -1) {
        String seqStr = message.substring(seqIndex + 4); // Get everything after "SEQ:"
        seqStr.trim();
        seqNum = seqStr.toInt();
        Serial.print("➡ Sequence Number from transmitter: ");
        Serial.println(seqNum);

        // Upload RSSI and SEQ to server
        uploadRSSI(seqNum, rssi);
      } else {
        Serial.println("⚠ No SEQ found in message");
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
    delay(1000);
  }

  Serial.println("\n✅ Connected to WiFi!");
  Serial.print("Local IP Address: ");
  Serial.println(WiFi.localIP());
}

// ----- Upload RSSI to Flask server -----
void uploadRSSI(int seq, int rssi) {
  String endpoint = "/RX002/data";  // Flask endpoint
  String payload = String("{\"message\":\"skywalker\",\"seq\":") + String(seq) +
                   String(",\"rssi\":") + String(rssi) + "}";

  Serial.print("⬆️ Uploading RSSI to ");
  Serial.println(endpoint);

  client.beginRequest();
  client.post(endpoint);
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Length", payload.length());
  client.beginBody();
  client.print(payload);
  client.endRequest();

  int statusCode = client.responseStatusCode();
  String response = client.responseBody();

  Serial.print("Server response (");
  Serial.print(statusCode);
  Serial.println("):");
  Serial.println(response);
}
