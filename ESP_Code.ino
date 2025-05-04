// Pin Definitions for ESP32
#define DATA_PIN   27    // Data pin connected to DS 
#define LATCH_PIN  14    // Latch pin connected to STCP 
#define CLOCK_PIN  12     // Clock pin connected to SHCP 
#define LDR_PIN 25     // Analog pin for LDR
#define LED_PIN 26     // Digital pin for LED
#define IR1_PIN 32
#define IR2_PIN 33
#define IR3_PIN 34
#define IR4_PIN 35
#define TRIG1_PIN  22
#define ECHO1_PIN  19
#define TRIG2_PIN  23
#define ECHO2_PIN  18
#define TRIG3_PIN  5
#define ECHO3_PIN  17
#define TRIG4_PIN  16
#define ECHO4_PIN  4

int counter = 0;

const int yellowDuration = 2;

const int ldrThreshold = 100;  // Adjust this based on your environment

bool emergencyTriggered = false;
int emergencyLane = -1;
const int emergencyDuration = 10;

int ledState[16] = {0}; // LED states: 0 = OFF, 1 = ON

// Green light duration (seconds) for each lane
int laneTimes[4] = {1, 1, 1, 1};

// Order of lane activation (change this to control the sequence)
int laneOrder[4] = {0, 0, 0, 0}; // Lane 1 → 3 → 2 → 4

// LED Indexes per lane (Updated to match the new lane configuration)
const int greenLEDs[4]  = {1, 4, 9, 12};  // Green
const int yellowLEDs[4] = {2, 5, 10, 13};   // Yellow
const int redLEDs[4]    = {3, 6, 11, 14};   // Red

void setup() {
  pinMode(DATA_PIN, OUTPUT);
  pinMode(CLOCK_PIN, OUTPUT);
  pinMode(LATCH_PIN, OUTPUT);
  pinMode(LDR_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(IR1_PIN, INPUT_PULLUP);
  pinMode(IR2_PIN, INPUT_PULLUP);
  pinMode(IR3_PIN, INPUT_PULLUP);
  pinMode(IR4_PIN, INPUT_PULLUP);
  pinMode(TRIG1_PIN, OUTPUT);
  pinMode(ECHO1_PIN, INPUT);
  pinMode(TRIG2_PIN, OUTPUT);
  pinMode(ECHO2_PIN, INPUT);
  pinMode(TRIG3_PIN, OUTPUT);
  pinMode(ECHO3_PIN, INPUT);
  pinMode(TRIG4_PIN, OUTPUT);
  pinMode(ECHO4_PIN, INPUT);

  Serial.begin(9600);
}

void loop() {
  Serial.println("Ready");

  delay(100); // Let Python catch the "Ready" line

  readAllUltrasonics(); // Send ultrasonic data immediately after "Ready"

  // Wait up to 5 seconds for serial input
  unsigned long startTime = millis();
  while (millis() - startTime < 5000) {
    checkSerialInput();
    delay(10);  // brief delay to avoid hogging CPU
  } 

  ldrLoop();

  // Process the traffic lights only if data has been received
  for (int i = 0; i < 4; i++) {
    ldrLoop();

    if (handleEmergencyIfDetected()) {
      // Emergency handled → exit this cycle and restart
      break;
    }

    int laneIndex = laneOrder[i];
    int duration = laneTimes[laneIndex];
    handleSingleLane(laneIndex, duration);
  }
  delay(10000);
}

// Turn off all lights
void clearAllLights() {
  for (int i = 0; i < 16; i++) {
    ledState[i] = 0;
  }
}

// Push ledState[] to the shift registers
void shiftOutData() {
  digitalWrite(LATCH_PIN, LOW);
  for (int i = 15; i >= 0; i--) {
    digitalWrite(CLOCK_PIN, LOW);
    digitalWrite(DATA_PIN, ledState[i]);
    digitalWrite(CLOCK_PIN, HIGH);
  }
  digitalWrite(LATCH_PIN, HIGH);
}

// For handling current traffic light
void handleSingleLane(int laneIndex, int duration) {
  char laneLabel = '1' + laneIndex;

  // Turn on green for current lane
  clearAllLights();
  ledState[greenLEDs[laneIndex]] = 1;

  // Turn on red for all other lanes
  for (int j = 0; j < 4; j++) {
    if (j != laneIndex) ledState[redLEDs[j]] = 1;
  }

  shiftOutData();
  delay(duration * 1000);  // Green light for (duration - 5) seconds

  // Switch to yellow
  ledState[greenLEDs[laneIndex]] = 0;
  ledState[yellowLEDs[laneIndex]] = 1;
  shiftOutData();
  delay(yellowDuration * 1000);  // Yellow light for 5 seconds
}

int getStableLDRReading(int pin, int samples = 10) {
  long total = 0;
  for (int i = 0; i < samples; i++) {
    total += analogRead(pin);
    delay(5);
  }
  return total / samples;
}

// Control for the ldr
void ldrLoop() {
  int ldrValue = getStableLDRReading(LDR_PIN);

  if (ldrValue < ldrThreshold) {
    digitalWrite(LED_PIN, HIGH);  // It's dark → turn on LED
  } else {  
    digitalWrite(LED_PIN, LOW);   // It's bright → turn off LED
  }
  delay(500);
}

bool handleEmergencyIfDetected() {
  // Detect which IR sensor is LOW
  if (digitalRead(IR1_PIN) == HIGH) {
    emergencyLane = 0;
  } else if (digitalRead(IR2_PIN) == HIGH) {
    emergencyLane = 1;
  } else if (digitalRead(IR3_PIN) == HIGH) {
    emergencyLane = 2;
  } else if (digitalRead(IR4_PIN) == HIGH) {
    emergencyLane = 3;
  } else {
    emergencyLane = -1;
  }

  if (emergencyLane != -1) {
    handleSingleLane(emergencyLane, emergencyDuration);

    emergencyLane = -1; // Reset
    return true;        // Signal that emergency occurred
  }

  return false;         // No emergency
}

int isConsistentlyClose(int trigPin, int echoPin, int threshold = 5, int requiredHits = 10) {
  int hitCount = 0;

  for (int i = 0; i < requiredHits; i++) {
    // Trigger ultrasonic
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    long duration = pulseIn(echoPin, HIGH, 30000);  // timeout 30 ms
    long distance = duration * 0.034 / 2;

    if (distance > 0 && distance < threshold) {
      hitCount++;
    }

    delay(5);  // small delay between samples
  }

  return (hitCount >= requiredHits) ? 1 : 0;
}

void readAllUltrasonics() {
  int c1 = isConsistentlyClose(TRIG1_PIN, ECHO1_PIN);
  int c2 = isConsistentlyClose(TRIG2_PIN, ECHO2_PIN);
  int c3 = isConsistentlyClose(TRIG3_PIN, ECHO3_PIN);
  int c4 = isConsistentlyClose(TRIG4_PIN, ECHO4_PIN);

  String ultrasonicData = "Ultra,L1," + String(c1) + ",L2," + String(c2) + ",L3," + String(c3) + ",L4," + String(c4);

  Serial.println(ultrasonicData);

  delay(500);
}

void checkSerialInput() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.startsWith("Times,")) {
      // Expected format: Times,10,12,9,11
      input.remove(0, 6); // Remove "Times,"
      int index = 0;
      while (input.length() > 0 && index < 4) {
        int commaIndex = input.indexOf(',');
        String val = (commaIndex != -1) ? input.substring(0, commaIndex) : input;
        laneTimes[index++] = val.toInt();
        input = (commaIndex != -1) ? input.substring(commaIndex + 1) : "";
      }
    } else if (input.startsWith("Order,")) {
      // Expected format: Order,0,2,1,3
      input.remove(0, 6); // Remove "Order,"
      int index = 0;
      while (input.length() > 0 && index < 4) {
        int commaIndex = input.indexOf(',');
        String val = (commaIndex != -1) ? input.substring(0, commaIndex) : input;
        laneOrder[index++] = val.toInt();
        input = (commaIndex != -1) ? input.substring(commaIndex + 1) : "";
      }
    }
  }
}
