#define PRESENCE_PIN D2
#define RELAY_PIN    D5

const int RELAY_ON  = LOW;   // Active LOW: LOW를 출력해야 릴레이가 켜짐
const int RELAY_OFF = HIGH;

bool relayIsOn = false;

void setup() {
  Serial.begin(115200);

  pinMode(PRESENCE_PIN, INPUT);
  pinMode(RELAY_PIN, OUTPUT);

  digitalWrite(RELAY_PIN, RELAY_OFF);
  relayIsOn = false;

  Serial.println("=== 인체감지 스마트 조명 시작 ===");
}

void loop() {
  int presence = digitalRead(PRESENCE_PIN);

  if (presence == HIGH && !relayIsOn) {
    digitalWrite(RELAY_PIN, RELAY_ON);
    relayIsOn = true;
    Serial.println("사람 감지 -> LED ON");
  }
  else if (presence == LOW && relayIsOn) {
    digitalWrite(RELAY_PIN, RELAY_OFF);
    relayIsOn = false;
    Serial.println("사람 없음 -> LED OFF");
  }

  delay(20);
}
