// FForzano/xgsail-e1 — Apache-2.0. 발췌 (원본 firmware/sailframes_edge/sailframes_edge.ino)
void setup() {
  ledcAttach(TFT_BL_PIN, TFT_BL_PWM_FREQ, TFT_BL_PWM_RES);
  ledcWrite(TFT_BL_PIN, TFT_BL_DUTY_IDLE);
  pinMode(TFT_BL, OUTPUT);
}
