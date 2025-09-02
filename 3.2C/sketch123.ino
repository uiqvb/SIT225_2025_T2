#include "thingProperties.h"
#include <Arduino_LSM6DS3.h>
#include <math.h>

// -------- Tunables --------
const float SAMPLE_HZ        = 100.0f;   // sensor sample rate
const float DELTA_G_THRESH   = 3.0f;     // threshold for sudden impact (g)
const unsigned long ACTIVE_HOLD_MS = 600;  // keep impact_active ON this long
const unsigned long REFRACTORY_MS  = 500;  // time before relatching
const unsigned long PRINT_INTERVAL = 1000; // print every 1000 ms = 1 Hz

// Derived
const unsigned long SAMPLE_MS = (unsigned long)(1000.0f / SAMPLE_HZ);

// State
unsigned long lastSampleMs    = 0;
unsigned long impactHoldUntil = 0;
unsigned long lastLatchMs     = 0;
unsigned long lastPrintMs     = 0;

bool havePrev = false;
float prevAx = 0.0f, prevAy = 0.0f, prevAz = 0.0f;

void setup() {
  Serial.begin(115200);
  delay(1500);

  initProperties();
  ArduinoCloud.begin(ArduinoIoTPreferredConnection);

  if (!IMU.begin()) {
    Serial.println("IMU init failed!");
  }

  impact_active = false;
  impact_latch  = false;
  reset_request = false;

  Serial.println("Device ready. Printing values once per second...");
}

void loop() {
  ArduinoCloud.update();

  // Manual reset
  if (reset_request) {
    impact_latch  = false;
    reset_request = false;
  }

  const unsigned long now = millis();
  if (now - lastSampleMs < SAMPLE_MS) return;
  lastSampleMs = now;

  float x, y, z;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(x, y, z);

    if (!havePrev) {
      prevAx = x; prevAy = y; prevAz = z;
      havePrev = true;
      return;
    }

    float dx = fabsf(x - prevAx);
    float dy = fabsf(y - prevAy);
    float dz = fabsf(z - prevAz);

    prevAx = x; prevAy = y; prevAz = z;

    bool spike = (dx >= DELTA_G_THRESH) || (dy >= DELTA_G_THRESH) || (dz >= DELTA_G_THRESH);

    if (spike) {
      impact_active = true;
      impactHoldUntil = now + ACTIVE_HOLD_MS;

      if (now - lastLatchMs > REFRACTORY_MS) {
        impact_latch = true;
        lastLatchMs = now;
      }
    }

    if (impact_active && now > impactHoldUntil) {
      impact_active = false;
    }

    // -------- Print only once per second --------
    if (now - lastPrintMs >= PRINT_INTERVAL) {
      lastPrintMs = now;

      Serial.print("ax: "); Serial.print(x, 3);
      Serial.print(", ay: "); Serial.print(y, 3);
      Serial.print(", az: "); Serial.print(z, 3);

      Serial.print(", dx: "); Serial.print(dx, 3);
      Serial.print(", dy: "); Serial.print(dy, 3);
      Serial.print(", dz: "); Serial.print(dz, 3);

      Serial.print(", impact_active: ");
      Serial.print(impact_active ? "1" : "0");

      Serial.print(", impact_latch: ");
      Serial.println(impact_latch ? "1" : "0");
    }
  }
}
