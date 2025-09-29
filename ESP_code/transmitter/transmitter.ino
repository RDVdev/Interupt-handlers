#include <SPI.h>
#include <LoRa.h>

// Pin mapping for ESP32
#define SS      5   // NSS
#define RST     14  // RESET
#define DIO0    2   // DIO0
#define BUTTON_PIN 4  // Button pin with pull-up

// Global variables
volatile bool sendPacket = false;
int seqpacket = 0;
// Interrupt handler for button press
void IRAM_ATTR buttonISR() {
  sendPacket = true;
}

void setup() {
  Serial.begin(115200);
  while (!Serial);

  Serial.println("LoRa Transmitter");

  // Setup button with pull-up and interrupt
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(BUTTON_PIN), buttonISR, FALLING);

  // Setup LoRa transceiver module
  LoRa.setPins(SS, RST, DIO0);
  // LoRa.setTxPower(20);

  if (!LoRa.begin(868E6)) {   // Change to 868E6 or 915E6 depending on your region
    Serial.println("Starting LoRa failed!");
    while (1);
  }
  
  Serial.println("Press button to send packet...");
}

void loop() {
  if (sendPacket) {
    sendPacket = false; // Reset flag
    
    Serial.println("Button pressed! Sending packet...");
    
    LoRa.beginPacket();
    LoRa.print("skywalker:");
    LoRa.print(seqpacket);
    LoRa.endPacket();
    
    Serial.print("Packet sent: skywalker:");
    Serial.println(seqpacket);
    
    seqpacket = seqpacket + 1;
    
    // Small delay to debounce
    delay(200);
  }
  
  // Small delay to prevent excessive CPU usage
  delay(10);
}