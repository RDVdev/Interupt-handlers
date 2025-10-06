#include <SPI.h>
#include <LoRa.h>
#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>

// ------------------ LoRa / SPI Pins ------------------
// New wiring:
// SCK  -> D13 (GPIO 13)
// MOSI -> D11 (GPIO 11)
// MISO -> D12 (GPIO 12)
// NSS  -> D10 (GPIO 10)
// RESET-> D9  (GPIO 9)
// DIO1 -> D3  (GPIO 3)
// DIO0 -> D2  (GPIO 2)
#define SCK     13
#define MOSI    11
#define MISO    12
#define SS      10
#define RST     9
#define DIO1    3
#define DIO0    2

// ------------------ WiFi ------------------
const char* ssid = "OnePlus Nord CE3 5G";
const char* password = "help@2326";

// ------------------ Server ------------------
String baseServerUrl = "MorningStar.local:5000";
String deviceID = "receiver1";   // Change this to receiver1, receiver2, receiver3, etc.

void setup() {
  Serial.begin(115200);
  while (!Serial);

  Serial.print("Device ID: ");
  Serial.println(deviceID);
  
  // ---- WiFi connect ----
  Serial.print("Connecting to WiFi ");
  Serial.print(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");  

  // ---- LoRa init ----
  Serial.println("LoRa Receiver");
  LoRa.setPins(SS, RST, DIO0);
  if (!LoRa.begin(868E6)) {   // Change to 868E6 or 915E6 if needed
    Serial.println("Starting LoRa failed!");
    while (1);
  }
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String received = "";
    while (LoRa.available()) {
      received += (char)LoRa.read();
    }
    int rssi = LoRa.packetRssi();

    Serial.print("Received: ");
    Serial.print(received);
    Serial.print(" | RSSI: ");
    Serial.println(rssi);

    // Parse message and sequence number
    int colonIndex = received.indexOf(':');
    if (colonIndex > 0) {
      String message = received.substring(0, colonIndex);
      String seqStr = received.substring(colonIndex + 1);
      int seq = seqStr.toInt();

      // Verify if message equals "skywalker"
      if (message == "skywalker") {
        Serial.print("Valid skywalker message detected! Seq: ");
        Serial.println(seq);
        
        // ---- Upload to Flask server using ArduinoHttpClient ----
        if (WiFi.status() == WL_CONNECTED) {
          WiFiClient wifi;
          const char* server = "MorningStar.local";
          const uint16_t port = 5000;
          HttpClient httpClient(wifi, server, port);

          String url = "/" + deviceID + "/data";
          String payload = "{ \"message\": \"skywalker\", \"rssi\": " + String(rssi) + ", \"seq\": " + String(seq) + " }";

          httpClient.beginRequest();
          httpClient.post(url);
          httpClient.sendHeader("Content-Type", "application/json");
          httpClient.sendHeader("Content-Length", String(payload.length()));
          httpClient.beginBody();
          httpClient.print(payload);
          httpClient.endRequest();

          int statusCode = httpClient.responseStatusCode();
          String response = httpClient.responseBody();

          Serial.print("Server Response (");
          Serial.print(statusCode);
          Serial.print("): ");
          Serial.println(response);
        } else {
          Serial.println("WiFi disconnected!");
        }
      } else {
        Serial.println("Invalid message - not skywalker");
      }
    } else {
      Serial.println("Invalid packet format - no sequence number");
    }
  }
}
