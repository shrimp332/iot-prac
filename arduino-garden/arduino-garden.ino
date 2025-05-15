#include <ArduinoJson.h>

const int WATER_LED = 13;
const int DEBUG_LED = 13;

const int ULTRA_TRIG = 9;
const int ULTRA_ECHO = 10;

const int VALVE_RELAY = 12;

const int MOISTURE_SENSOR = A0;

void setup() {
  Serial.begin(9600);

  pinMode(WATER_LED, OUTPUT);

  pinMode(VALVE_RELAY, OUTPUT);

  pinMode(ULTRA_TRIG, OUTPUT);
  pinMode(ULTRA_ECHO, INPUT);

  delay(500);
}

void loop() {
  delay(1000);

  char buffer[100];

  collectSensorData();
  String input;
  if (Serial.available() > 0) {
    input = Serial.readStringUntil('\n');
  }

  if (input == "")
    return;

  JsonDocument incDoc;
  DeserializationError err = deserializeJson(incDoc, input.c_str());

  JsonDocument doc;
  if (err != DeserializationError::Ok) {
    doc["type"] = 5;
    doc["message"] = "Broken message: " + input;
    serializeJson(doc, buffer);
    Serial.println(buffer);
    return;
  }

  int type = incDoc["type"];
  bool state = incDoc["state"];
  switch (type) {
    case 0:
      if (state) {
        digitalWrite(VALVE_RELAY, HIGH);
        doc["type"] = 3;
        doc["message"] = "Confirmed: Valve Open";
        serializeJson(doc, buffer);
        Serial.println(buffer);
      } else {
        digitalWrite(VALVE_RELAY, LOW);
        doc["type"] = 3;
        doc["message"] = "Confirmed: Valve Closed";
        serializeJson(doc, buffer);
        Serial.println(buffer);
      }
      return;
    case 1:
      if (state) {
        digitalWrite(WATER_LED, HIGH);
      } else {
        digitalWrite(WATER_LED, LOW);
      }
      return;
    default:
      doc["type"] = 4;
      doc["message"] = "Unknown Command";
  }
}

void collectSensorData() {
  JsonDocument doc;
  doc["type"] = 2;

  // Soil Moisture
  float val = analogRead(MOISTURE_SENSOR);
  float moistness = (770.0f - val) / 3.2f;

  if (moistness < 0.0f) {
    moistness = 0.0f;
  }

  doc["data"][0] = moistness;

  // Reservoir
  digitalWrite(ULTRA_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRA_TRIG, LOW);
  long duration = pulseIn(ULTRA_ECHO, HIGH);

  constexpr long empty = 990.0L;  // max
  constexpr float full = 250.0L;  // min

  // (max - value) / (max - min)
  long capacity = 100.0L * (empty - duration) / (empty - full);

  if (capacity < 0.0L) {
    capacity = 0.0L;
  }

  doc["data"][1] = capacity;

  char buffer[100];
  serializeJson(doc, buffer);
  Serial.println(buffer);
}
