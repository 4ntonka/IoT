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

// Current LED state
int ledState = OFF;
unsigned long previousMillis = 0;
const long blinkInterval = 1000;  // 1 second blink interval

// put your setup code here
void setup() {
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);

  // initialize serial port and wait for port to open:
  Serial.begin(9600);

  // wait for serial port to connect. Needed for native USB port only
  // while (!Serial) {
  // }

  // init digital IO pins
  digitalWrite(LED_BUILTIN, LOW);

  // Print welcome message
  Serial.println("Arduino ready for commands (on, off, blink, status)");
}

// put your main code here
void loop() {
  // Check for incoming serial commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();  // Remove any whitespace/newlines

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
      if (ledState == ON) {
        Serial.println("LED on");
      } else if (ledState == OFF) {
        Serial.println("LED off");
      } else if (ledState == BLINK) {
        Serial.println("LED blink");
      }
    } else {
      Serial.println("Unknown command. Use: on, off, blink, or status");
    }
  }

  // Handle LED blinking if in blink mode
  if (ledState == BLINK) {
    unsigned long currentMillis = millis();
    if (currentMillis - previousMillis >= blinkInterval) {
      previousMillis = currentMillis;

      // Toggle LED state
      if (digitalRead(LED_BUILTIN) == HIGH) {
        digitalWrite(LED_BUILTIN, LOW);
      } else {
        digitalWrite(LED_BUILTIN, HIGH);
      }
    }
  }
}
