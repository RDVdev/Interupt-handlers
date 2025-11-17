#include <SPI.h>
#include <LoRa.h>

#define LORA_SS     10
#define LORA_RST    9
#define LORA_DIO0   2
#define LORA_DIO1   3   // Optional
#define BUTTON_PIN  4   // One side to GND, uses internal pull-up

const char* TEAM_ID = "skywalker";
int packetCount = 0;

void setup() {
  // Serial.begin(115200);
  // while (!Serial);

  // Serial.println("\n=== Initializing LoRa Transmitter ===");

  pinMode(BUTTON_PIN, INPUT_PULLUP);

  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(868E6)) {   // Use 915E6 for US region
    // Serial.println("LoRa init failed! Check wiring.");
    while (1);
  }

  // Configure LoRa parameters
  LoRa.setSyncWord(0xAB);                  // Must match receiver
  LoRa.setTxPower(20, PA_OUTPUT_PA_BOOST_PIN);
  LoRa.setSpreadingFactor(12);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(8);

  // Serial.println("LoRa Transmitter ready! Press the button to send packets.");
}

void loop() {
  static bool buttonPressed = false;

  if (digitalRead(BUTTON_PIN) == LOW && !buttonPressed) {
    buttonPressed = true;

    // Serial.println("Button pressed → Sending 2 packets...");

      sendPacket();
      packetCount++;
      delay(500); // delay between packets

    // Serial.println("✅ Done sending packets.");
  }

  // Wait until button released before next trigger
  if (digitalRead(BUTTON_PIN) == HIGH && buttonPressed) {
    buttonPressed = false;
  }
}

void sendPacket() {
  // Serial.print("Sending packet SEQ:");
  // Serial.println(packetCount + 1);

  LoRa.beginPacket();
  LoRa.print(TEAM_ID);
  LoRa.print(" SEQ:");
  LoRa.print(packetCount + 1);
  LoRa.endPacket();

  // Serial.println("→ Packet sent!");
}