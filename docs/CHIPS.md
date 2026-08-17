# 칩별 핀 제약 표

**⚠ 이 표는 초안입니다. 하드웨어 담당(한지양·권지효)의 검수 전에는 규칙에 넣지 않습니다.**
규칙의 정확성은 하드웨어 담당이 책임집니다. 아래 근거 링크를 직접 확인하고 표를 확정해 주세요.

---

## 왜 표로 만드나

규칙을 특정 칩에 하드코딩하면 다른 칩에서 **조용히 아무것도 안 잡습니다.**
"이상 없음"과 "이 칩에는 해당 없음"은 완전히 다른 말인데, 하드코딩하면 둘이 구별되지 않습니다.

그래서 규칙 함수는 칩을 모르고, 이 표만 봅니다.
표에 해당 항목이 없으면 `skipped` 로 사유와 함께 응답에 실립니다.

```python
# 규칙은 이렇게 생겼다 — 핀 번호를 규칙 안에 적지 않는다
def check(ctx):
    forbidden = ctx.chip.pins.forbidden      # 표에서 온다
    if not forbidden:
        return skipped("이 칩에는 해당 제약이 없습니다")
    ...
```

---

## ESP32 (구형, ESP32-D0WD 계열)

| 분류 | 핀 | 의미 |
|---|---|---|
| 입력 전용 | GPIO34, 35, 36, 37, 38, 39 | OUTPUT 설정 불가. 내부 풀업/풀다운도 없음 |
| SPI 플래시 | GPIO6 ~ GPIO11 | 내장 플래시 전용. 다른 용도로 쓰면 부팅 실패 |
| 스트래핑 | GPIO0, 2, 5, 12, 15 | 부팅 시 레벨이 부팅 모드를 결정 |
| ADC1 | GPIO32 ~ 39 | WiFi와 무관하게 사용 가능 |
| ADC2 | GPIO0, 2, 4, 12 ~ 15, 25 ~ 27 | **WiFi 구동 중 사용 불가** |

## ESP32-C6

| 분류 | 핀 | 의미 |
|---|---|---|
| 입력 전용 | **없음** | GPIO0~30 전부 양방향 |
| SPI 플래시 | GPIO24 ~ GPIO30 | 내장 플래시 전용. 다른 용도 비권장 |
| 스트래핑 | GPIO4, 5, 8, 9, 15 | GPIO8·9는 부팅 모드, GPIO15는 JTAG 소스 선택 |
| ADC1 | GPIO0 ~ GPIO6 | 7채널 |
| ADC2 | **없음** | 칩에 ADC2가 존재하지 않음 |

### C6에서 주의할 겹침

ADC 채널(GPIO0~6)과 스트래핑 핀(GPIO4, 5)이 **겹칩니다.**
GPIO4·5를 아날로그 입력으로 쓰면 부팅 시점의 레벨이 부팅 모드에 영향을 줄 수 있습니다.

---

## 규칙이 칩별로 어떻게 갈리나

| 규칙 | ESP32 (구형) | ESP32-C6 |
|---|---|---|
| **R1** 코드가 쓸 수 없는 핀을 사용 | 입력 전용 핀에 OUTPUT → `CRITICAL` | 플래시 핀 사용 → `CRITICAL`<br>스트래핑 핀 사용 → `WARNING` |
| **R5** 칩이 지원하지 않는 조합 | ADC2 + WiFi 동시 → `CRITICAL` | ADC2 없음 → `skipped`<br>ADC(GPIO4·5) + 스트래핑 겹침 → `WARNING` |
| **R7·R8·R10** 코드 ↔ 회로도 대조 | 칩 무관 | 칩 무관 |

**R1과 R5는 칩마다 내용이 다를 뿐 양쪽 다 살아 있습니다.**
C6에서 못 하는 항목은 숨기지 않고 `skipped` + 사유로 내보냅니다.

R7·R8·R10은 칩과 무관합니다. 코드가 참조하는 핀과 넷리스트의 연결을 비교하는 것뿐이라서요.
**차별 등급의 중심은 이쪽입니다.**

---

## 아직 못 채운 칸 — 모듈 핀아웃

칩 핀 번호를 알아도 **보드 실크 라벨과 매칭이 안 됩니다.**

우리 보드(XIAO ESP32-C6)의 넷리스트에서 U1의 핀 이름은 이렇게 나옵니다.

```
3V3, 3V3_, 5V, BAT, BOOT, D10_, D7_R, D8_S, D9_M,
EN, GND, GND_, GPIO, LP-G, LP-I, MTDI, MTMS, SDIO
```

IPC-D-356이 핀 이름을 **4자에서 자르기 때문**입니다. `LP-GPIO0` → `LP-G` 가 됩니다.
`D7_R` 가 어느 GPIO인지 이 파일만으로는 알 수 없습니다.

그래서 **모듈 핀아웃 DB**가 필요합니다.

```jsonc
// 이런 형태
{
  "XIAO-ESP32C6": {
    "chip": "esp32c6",
    "pins": { "D0": "GPIO0", "D1": "GPIO1", "D2": "GPIO2", "...": "..." }
  }
}
```

이게 없으면 R1·R5·R7·R8이 **우리 보드에서 전부 못 돕니다.**
지금 도는 R11·R12는 전원 도메인만 보기 때문에 핀 번호가 필요 없었을 뿐입니다.

> 하드웨어 담당께: XIAO ESP32-C6의 실크 라벨 → GPIO 번호 대응표가 가장 급합니다.
> Seeed 공식 핀아웃 문서를 그대로 옮겨 적으면 됩니다.

---

## 근거

- [ESP32-C6 Datasheet — Espressif](https://documentation.espressif.com/esp32-c6_datasheet_en.html)
- [GPIO & RTC GPIO — ESP32-C6, ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c6/api-reference/peripherals/gpio.html)
- [Boot Mode Selection — ESP32-C6, esptool](https://docs.espressif.com/projects/esptool/en/latest/esp32c6/advanced-topics/boot-mode-selection.html)
- [ADC2 / WiFi 충돌 — ESP-IDF](https://github.com/espressif/esp-idf/blob/v4.0.3/docs/en/api-reference/peripherals/adc.rst)

표를 고칠 때는 **근거 링크를 함께 남깁니다.** 출처 없는 핀 번호는 규칙에 넣지 않습니다.
