// ========================================
// XIAO ESP32-C6
// HC-SR04 + LED 테스트
// ========================================
//
// [픽스처 주의]
// 팀원이 준 esp32-c6-presence-smart-light 보드의 **펌웨어 초판**을 그대로 보존한 것이다.
// 그 뒤 프로젝트 주제가 바뀌어 회로도만 앞서갔고, 이 코드는 초음파 시절에 멈춰 있다.
// 즉 이 파일과 같은 폴더의 .d356 은 **실제로 어긋난 한 쌍**이다.
//
// 고치지 말 것. 어긋남이 이 픽스처의 존재 이유다.
// R7 · R8 골든 테스트의 입력이며, 기대 발견은 ../esp32-c6-presence-smart-light.EXPECTED.md 에 있다.

const int TRIG_PIN = D2;
const int ECHO_PIN = D3;
const int LED_PIN  = D10;

// 사람으로 판단할 거리
const float DETECT_DISTANCE = 100.0;  // cm


void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  pinMode(LED_PIN, OUTPUT);

  digitalWrite(TRIG_PIN, LOW);
  digitalWrite(LED_PIN, LOW);

  delay(1000);

  Serial.println("=== Smart Shoe Cabinet Test ===");
}


void loop() {

  // -------------------------
  // 1. 초음파 발사
  // -------------------------

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);


  // -------------------------
  // 2. ECHO 시간 측정
  // -------------------------

  unsigned long duration =
      pulseIn(ECHO_PIN, HIGH, 50000);


  // -------------------------
  // 3. 거리 계산
  // -------------------------

  if (duration == 0) {

    Serial.println("NO ECHO");

    // 센서가 사람을 못 찾으면 LED OFF
    digitalWrite(LED_PIN, LOW);

  }
  else {

    float distance =
        duration * 0.0343 / 2.0;


    Serial.print("Distance: ");
    Serial.print(distance);
    Serial.println(" cm");


    // -------------------------
    // 4. 사람 감지 → LED ON
    // -------------------------

    if (distance > 0 &&
        distance <= DETECT_DISTANCE) {

      Serial.println("PERSON DETECTED!");
      digitalWrite(LED_PIN, HIGH);

    }
    else {

      Serial.println("NO PERSON");
      digitalWrite(LED_PIN, LOW);

    }
  }


  delay(200);
}
