#include "thingProperties.h"
#include <DHT.h>

#define DHTPIN 7
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(9600);
  dht.begin();

  // Connect to Arduino Cloud
  initProperties();
  ArduinoCloud.begin(ArduinoIoTPreferredConnection);

  // Optional: Wait until connected
  setDebugMessageLevel(2);
  ArduinoCloud.printDebugInfo();
}

void loop() {
  ArduinoCloud.update(); // 🔁 Mandatory to keep cloud connection alive

  // Read DHT22 data
  humidity = dht.readHumidity();
  temperature = dht.readTemperature();

  // Optional: Print to Serial Monitor
  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.print(" %\tTemperature: ");
  Serial.print(temperature);
  Serial.println(" C");

  delay(1000); // Wait 5 seconds before reading again
}
