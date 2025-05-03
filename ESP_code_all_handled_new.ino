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

const int yellowDuration = 5;

const int ldrThreshold = 1000;  // Adjust this based on your environment

bool emergencyTriggered = false;
int emergencyLane = -1;
const int emergencyDuration = 10;

int ledState[16] = {0}; // LED states: 0 = OFF, 1 = ON

// Green light duration (seconds) for each lane
int laneTimes[4] = {10, 12, 9, 11};

// Order of lane activation (change this to control the sequence)
int laneOrder[4] = {0, 2, 1, 3}; // Lane 1 → 3 → 2 → 4

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
  Serial.println("Smart Traffic Controller with Custom Lane Order");
}

void loop() {
  ldrLoop();
  
  if (Serial.available()) {
    // Wait for new input before each cycle
    String inputData = Serial.readStringUntil('\n');  // Read the incoming data as a string
    Serial.println("Received from Python: " + inputData);
    processIncomingData(inputData);  // Process the received data

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

    // Cycle done → notify Python, send ultrasonic data and wait for next input
    readAllUltrasonics();
  } else {
    // Keep all lights red while waiting
    clearAllLights();
    shiftOutData();
    delay(100);  // Small delay to avoid overwhelming the loop
  }
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

  Serial.print("Lane ");
  Serial.print(laneLabel);
  Serial.print(" -> GREEN for ");
  Serial.print(duration - yellowDuration);    
  Serial.println("s, then YELLOW for ");
  Serial.print(yellowDuration);
  Serial.print("s");

  // Turn on green for current lane
  clearAllLights();
  ledState[greenLEDs[laneIndex]] = 1;

  // Turn on red for all other lanes
  for (int j = 0; j < 4; j++) {
    if (j != laneIndex) ledState[redLEDs[j]] = 1;
  }

  shiftOutData();
  delay((duration - yellowDuration) * 1000);  // Green light for (duration - 5) seconds

  // Switch to yellow
  ledState[greenLEDs[laneIndex]] = 0;
  ledState[yellowLEDs[laneIndex]] = 1;
  shiftOutData();
  delay(yellowDuration * 1000);  // Yellow light for 5 seconds
}

// Control for the ldr
void ldrLoop() {
  int ldrValue = analogRead(LDR_PIN);
  Serial.print("LDR Value: ");
  Serial.println(ldrValue);

  if (ldrValue < ldrThreshold) {
    digitalWrite(LED_PIN, HIGH);  // It's dark → turn on LED
  } else {
    digitalWrite(LED_PIN, LOW);   // It's bright → turn off LED
  }
}

bool handleEmergencyIfDetected() {
  // Detect which IR sensor is LOW
  if (digitalRead(IR1_PIN) == LOW) {
    emergencyLane = 0;
  } else if (digitalRead(IR2_PIN) == LOW) {
    emergencyLane = 1;
  } else if (digitalRead(IR3_PIN) == LOW) {
    emergencyLane = 2;
  } else if (digitalRead(IR4_PIN) == LOW) {
    emergencyLane = 3;
  } else {
    emergencyLane = -1;
  }

  if (emergencyLane != -1) {
    Serial.print("Emergency in Lane ");
    Serial.print(emergencyLane + 1);
    Serial.println(" → Prioritizing for 10s");

    handleSingleLane(emergencyLane, emergencyDuration);

    emergencyLane = -1; // Reset
    return true;        // Signal that emergency occurred
  }

  return false;         // No emergency
}

long readUltrasonic(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 30000);  // timeout: 30 ms
  long distance = duration * 0.034 / 2;  // cm

  return distance; // if timeout, will return 0
}

void readAllUltrasonics() {
  long d1 = readUltrasonic(TRIG1_PIN, ECHO1_PIN);
  long d2 = readUltrasonic(TRIG2_PIN, ECHO2_PIN);
  long d3 = readUltrasonic(TRIG3_PIN, ECHO3_PIN);
  long d4 = readUltrasonic(TRIG4_PIN, ECHO4_PIN);

  int c1 = (d1 < 18) ? 1 : 0;
  int c2 = (d2 < 18) ? 1 : 0;
  int c3 = (d3 < 18) ? 1 : 0;
  int c4 = (d4 < 18) ? 1 : 0;

  // Prepare the ultrasonic data in CSV format with "Ultra" prefix for easy parsing
  String ultrasonicData = "Ultra,L1," + String(c1) + ",L2," + String(c2) + ",L3," + String(c3) + ",L4," + String(c4);

  // Send the "Ready" message and the ultrasonic data
  Serial.println("Ready");
  Serial.println(ultrasonicData);

  delay(500);
}

void processIncomingData(String inputData) {
  // Example of expected input format from Python: "laneTimes:10,12,9,11;laneOrder:0,2,1,3"
  int laneTimesStart = inputData.indexOf("laneTimes:") + 10;
  int laneOrderStart = inputData.indexOf("laneOrder:") + 10;
  
  // Extract laneTimes values
  String laneTimesStr = inputData.substring(laneTimesStart, inputData.indexOf(";", laneTimesStart));
  int prevIndex = 0;
  int laneIndex = 0;
  while (laneTimesStr.indexOf(",", prevIndex) != -1) {
    laneTimes[laneIndex++] = laneTimesStr.substring(prevIndex, laneTimesStr.indexOf(",", prevIndex)).toInt();
    prevIndex = laneTimesStr.indexOf(",", prevIndex) + 1;
  }
  laneTimes[laneIndex] = laneTimesStr.substring(prevIndex).toInt();  // Last value

  // Extract laneOrder values
  String laneOrderStr = inputData.substring(laneOrderStart);
  prevIndex = 0;
  laneIndex = 0;
  while (laneOrderStr.indexOf(",", prevIndex) != -1) {
    laneOrder[laneIndex++] = laneOrderStr.substring(prevIndex, laneOrderStr.indexOf(",", prevIndex)).toInt();
    prevIndex = laneOrderStr.indexOf(",", prevIndex) + 1;
  }
  laneOrder[laneIndex] = laneOrderStr.substring(prevIndex).toInt();  // Last value
}