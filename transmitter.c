#include <SPI.h>
#include <LoRa.h>

// Pin mapping for ESP32
#define SS      5   // NSS
#define RST     14  // RESET
#define DIO0    2   // DIO0

void setup() {
  Serial.begin(115200);
  while (!Serial);

  Serial.println("LoRa Transmitter");

  // Setup LoRa transceiver module
  LoRa.setPins(SS, RST, DIO0);
  // LoRa.setTxPower(20);

  if (!LoRa.begin(868E6)) {   // Change to 868E6 or 915E6 depending on your region
    Serial.println("Starting LoRa failed!");
    while (1);
  }
}

void loop() {
  Serial.println("Sending packet...");
  
  LoRa.beginPacket();
  LoRa.print("Hello from interuppt handlers");
  LoRa.endPacket();

  delay(2000); // send every 2 seconds
}