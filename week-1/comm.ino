void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(9600);
  randomSeed(analogRead(0));
}

void loop() {
  if (Serial.available() > 0) {
    int num = Serial.parseInt();
    if (num > 0) {
      // Blink LED 'num' times
      for (int i = 0; i < num; i++) {
        digitalWrite(LED_BUILTIN, HIGH);
        delay(500);
        digitalWrite(LED_BUILTIN, LOW);
        delay(500);
      }

      // Send random number back (1 to 5)
      int randNum = random(1, 6);
      Serial.println(randNum);
    }
  }
}
