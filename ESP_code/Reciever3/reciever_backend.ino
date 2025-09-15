#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <HTTPClient.h>

// ------------------ LoRa Pins ------------------
#define SS      5
#define RST     14
#define DIO0    2

// ------------------ WiFi ------------------
const char* ssid = "OnePlus Nord CE3 5G";
const char* password = "help@2326";

// ------------------ Server ------------------
String baseServerUrl = "http://10.23.123.216:5000";
String deviceID = "receiver3";   // Change this to receiver1, receiver2, receiver3, etc.

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

    // Verify if message equals "skywalker"
    if (received == "skywalker") {
      Serial.println("Valid skywalker message detected!");
      
      // ---- Upload to Flask server ----
      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;

        String endpoint = baseServerUrl + "/" + deviceID + "/data";
        http.begin(endpoint);

        http.addHeader("Content-Type", "application/json");

        // JSON payload with message and RSSI
        String payload = "{ \"message\": \"skywalker\", \"rssi\": " + String(rssi) + " }";

        int httpResponseCode = http.POST(payload);

        if (httpResponseCode > 0) {
          Serial.print("Server Response (");
          Serial.print(httpResponseCode);
          Serial.print("): ");
          Serial.println(http.getString());
        } else {
          Serial.print("Error code: ");
          Serial.println(httpResponseCode);
        }

        http.end();
      } else {
        Serial.println("WiFi disconnected!");
      }
    } else {
      Serial.println("Invalid message - not skywalker");
    }
  }
}
