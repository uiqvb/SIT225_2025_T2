/*
    Ahsan Habib (habib@deakin.edu.au),
    School of Information Technology,
    Deakin University, Australia.
*/

// Add Arduino_LSM6DS3 library 
// from Arduino IDE Library Manager.
#include <Arduino_LSM6DS3.h>

float x, y, z;

void setup() {
  Serial.begin(9600); // set baud rate
  while (!Serial);  // wait for port to init
  Serial.println("Started");

  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }

  Serial.println(
    "Accelerometer sample rate = " 
    + String(IMU.accelerationSampleRate()) + " Hz");
}

void loop() {
  // read accelero data
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(x, y, z);
  }
  
  Serial.println(
    String(x) + ", " + String(y) + ", " + String(z));
  
  delay(1000);
}
