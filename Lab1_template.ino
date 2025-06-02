// -------------------------------------------
//
//  Poject: Lab1_task1
//  Group:
//  Students:
//  Date:
//  ------------------------------------------

#define OFF 0
#define ON 1

// put your setup code here
void setup() {
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);

  // initialize serial port and wait for port to open:
  Serial.begin(9600);

  // wait for serial port to connect. Needed for native USB port only
  while (!Serial) {
  }

  // init digital IO pins
  digitalWrite(LED_BUILTIN, LOW);
}

// put your main code here
void loop() {
  // turn the LED on
  digitalWrite(LED_BUILTIN, HIGH);
  // wait for 1000 milliseconds (1 second)
  delay(1000);

  // turn the LED off
  digitalWrite(LED_BUILTIN, LOW);
  // wait for 1000 milliseconds (1 second)
  delay(1000);
}
