// -------------------------------------------
//
//  Project: Lab1_task1 - Serial Communication with Python
//  Group:
//  Students:
//  Date:
//  ------------------------------------------

#define OFF 0
#define ON 1
#define BLINK 2

int ledState = OFF;
unsigned long previousMillis = 0;
const long blinkInterval = 1000;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(9600);
  digitalWrite(LED_BUILTIN, LOW);
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "on") {
      ledState = ON;
      digitalWrite(LED_BUILTIN, HIGH);
      Serial.println("LED on");
    } else if (command == "off") {
      ledState = OFF;
      digitalWrite(LED_BUILTIN, LOW);
      Serial.println("LED off");
    } else if (command == "blink") {
      ledState = BLINK;
      Serial.println("LED blink");
    } else if (command == "status") {
      Serial.println(
          ledState);  // Just return the state as a number (0, 1, or 2)
    } else {
      Serial.println("Unknown command. Use: on, off, blink, or status");
    }
  }

  if (ledState == BLINK) {
    unsigned long currentMillis = millis();
    if (currentMillis - previousMillis >= blinkInterval) {
      previousMillis = currentMillis;
      if (digitalRead(LED_BUILTIN) == HIGH) {
        digitalWrite(LED_BUILTIN, LOW);
      } else {
        digitalWrite(LED_BUILTIN, HIGH);
      }
    }
  }
}
