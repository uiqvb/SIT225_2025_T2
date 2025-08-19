#include <Arduino_LSM6DS3.h>

// setup runs once
void setup() {
  Serial.begin(9600);

  // wait until Serial is ready
  while (!Serial) {
    // just waiting
  }

  // start the IMU
  if (IMU.begin() == false) {
    Serial.println("IMU not detected!");
    while (true) {
      // stop here forever
    }
  }

  Serial.println("Gyroscope ready.");
}

// loop runs forever
void loop() {
  float gx, gy, gz; // different variable names

  // if new gyro data is there, read it
  if (IMU.gyroscopeAvailable()) {
    IMU.readGyroscope(gx, gy, gz);

    // build the output
    Serial.print("x:");
    Serial.print(gx, 2);
    Serial.print(",y:");
    Serial.print(gy, 2);
    Serial.print(",z:");
    Serial.println(gz, 2);
  }

  // pause a little bit
  delay(5000);
}
