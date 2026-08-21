/*
  인체감지 스마트 조명 - 2N3904 트랜지스터 레벨시프트 적용

  배선:
    XIAO D5 --[1kΩ]-- 2N3904 베이스(B)
    2N3904 이미터(E) -- GND
    2N3904 컬렉터(C) -- 릴레이 IN
    릴레이 IN -- R3(10kΩ) -- 5V_BUS (3V3 아님)

  신호 반전:
    D5 = HIGH(3.3V) -> 트랜지스터 ON  -> 릴레이 IN = LOW     -> 릴레이 ON
    D5 = LOW(0V)    -> 트랜지스터 OFF -> 릴레이 IN = HIGH(5V) -> 릴레이 OFF
*/

#define PRESENCE_PIN D2
#define RELAY_PIN    D5

bool relayIsOn = false;

void setup() {
  Serial.begin(115200);

  pinMode(PRESENCE_PIN, INPUT);
  pinMode(RELAY_PIN, OUTPUT);

  digitalWrite(RELAY_PIN, LOW);
  relayIsOn = false;

  Serial.println("=== 인체감지 스마트 조명 시작 (2N3904 반전 적용) ===");
}

void loop() {
  int presence = digitalRead(PRESENCE_PIN);

  if (presence == HIGH && !relayIsOn) {
    digitalWrite(RELAY_PIN, HIGH);
    relayIsOn = true;
    Serial.println("사람 감지 -> LED ON");
  }
  else if (presence == LOW && relayIsOn) {
    digitalWrite(RELAY_PIN, LOW);
    relayIsOn = false;
    Serial.println("사람 없음 -> LED OFF");
  }

  delay(20);
}
