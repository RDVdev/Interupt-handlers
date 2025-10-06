#include <SPI.h>
#include <LoRa.h>

// Pin mapping for ESP32
#define SCK     13
#define MOSI    11
#define MISO    12
#define SS      10
#define RST     9
#define DIO1    3
#define DIO0    2
#define BUTTON_PIN 4

// Global variables
volatile bool sendPacket = false;
int seqpacket = 0;
int buttonDebounceCounter = 0;
int debounceInterval = 250;
// Interrupt handler for button press
void IRAM_ATTR buttonISR() {
  if(buttonDebounceCounter + debounceInterval <= millis()){
    sendPacket = true;
    buttonDebounceCounter = millis();
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial);
  buttonDebounceCounter = millis();

  Serial.println("LoRa Transmitter");
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(BUTTON_PIN), buttonISR, FALLING);
  LoRa.setPins(SS, RST, DIO0);

  if (!LoRa.begin(868E6)) {
    Serial.println("Starting LoRa failed!");
    while (1);
  }
  
  // Configure LoRa parameters
  LoRa.setTxPower(20);        // Set TX power to 20 dBm
  LoRa.setSpreadingFactor(12); // Set spreading factor to 12
  
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