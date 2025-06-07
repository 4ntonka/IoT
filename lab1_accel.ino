// -------------------------------------------
//
//  Project: Lab1_task1 - Serial Communication with Python
//  Group: 4
//  Students: Nathaniel Kamperveen, Anton Smirnov
//  Date: 6-6-2025
//  ------------------------------------------

#include <Arduino_LSM6DS3.h>

void setup() {
  Serial.begin(9600);
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }
}

void loop() {
  float x, y, z;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(x, y, z);
    Serial.print(x, 4);
    Serial.print(",");
    Serial.print(y, 4);
    Serial.print(",");
    Serial.println(z, 4);
  }
  delay(100);
}
