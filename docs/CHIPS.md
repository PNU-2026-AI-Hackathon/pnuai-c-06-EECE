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
| 부팅 중 출력 | GPIO1 (U0TXD) | 펌웨어가 돌기 전에 부팅 로그가 나온다 |

## ESP32-C6

| 분류 | 핀 | 의미 |
|---|---|---|
| 입력 전용 | **없음** | GPIO0~30 전부 양방향 |
| SPI 플래시 | GPIO24 ~ GPIO30 | 내장 플래시 전용. 다른 용도 비권장 |
| 스트래핑 | GPIO4, 5, 8, 9, 15 | GPIO8·9는 부팅 모드, GPIO15는 JTAG 소스 선택 |
| ADC1 | GPIO0 ~ GPIO6 | 7채널 |
| ADC2 | **없음** | 칩에 ADC2가 존재하지 않음 |
| 부팅 중 출력 | GPIO16 (U0TXD) | 펌웨어가 돌기 전에 부팅 로그가 나온다 |

### C6에서 주의할 겹침

ADC 채널(GPIO0~6)과 스트래핑 핀(GPIO4, 5)이 **겹칩니다.**
GPIO4·5를 아날로그 입력으로 쓰면 부팅 시점의 레벨이 부팅 모드에 영향을 줄 수 있습니다.

---

## 규칙이 칩별로 어떻게 갈리나

| 규칙 | ESP32 (구형) | ESP32-C6 |
|---|---|---|
| **R1** 코드가 쓸 수 없는 핀을 사용 | 입력 전용 핀에 OUTPUT → `CRITICAL` | 플래시 핀 사용 → `CRITICAL`<br>스트래핑 핀 사용 → `WARNING` |
| **R2** 회로도가 플래시 핀에 배선 | GPIO6~11 배선 → `CRITICAL` | GPIO24~30 배선 → `CRITICAL` |
| **R3** 스트래핑 핀이 전원·접지 직결 | GPIO0·2·5·12·15 → `WARNING` | GPIO4·5·8·9·15 → `WARNING` |
| **R9** 부팅 중 출력 핀에 무언가 붙음 | GPIO1 에 연결 → `정보` | GPIO16 에 연결 → `정보` |
| **R5** 칩이 지원하지 않는 조합 | ADC2 + WiFi 동시 → `CRITICAL` | ADC2 없음 → `skipped`<br>ADC(GPIO4·5) + 스트래핑 겹침 → `WARNING` |
| **R7·R8·R10** 코드 ↔ 회로도 대조 | 칩 무관 | 칩 무관 |

**R2·R3 은 회로도만 봅니다.** R1 이 같은 핀을 코드 쪽에서 보는 것과 짝입니다 —
코드가 안 써도 배선 자체가 문제인 경우를 R2·R3 이 잡습니다.

두 규칙 모두 **오탐 경계를 좁게 잡았습니다.**
- R2 는 플래시 핀 여러 가닥이 한 부품으로 모이면 그것을 플래시 IC 로 보고 넘어갑니다.
  맨칩 설계에서 외부 플래시로 가는 배선은 정상이기 때문입니다.
- R3 은 **직결만** 잡습니다. 저항·스위치를 거치면 패드가 다른 네트에 있어 안 걸립니다.
  풀업 저항과 부트 버튼은 정상 설계입니다.

**R1과 R5는 칩마다 내용이 다를 뿐 양쪽 다 살아 있습니다.**
C6에서 못 하는 항목은 숨기지 않고 `skipped` + 사유로 내보냅니다.

R7·R8·R10은 칩과 무관합니다. 코드가 참조하는 핀과 넷리스트의 연결을 비교하는 것뿐이라서요.
**차별 등급의 중심은 이쪽입니다.**

---

## 모듈 핀아웃 — XIAO ESP32-C6

칩 핀 번호를 알아도 **보드 실크 라벨과 매칭이 안 된다.**
IPC-D-356 이 핀 이름을 **4자에서 자르기 때문**이다.

우리 보드(U1)의 넷리스트 레코드는 **25개인데 이름 종류는 18개**다.
물리적으로 다른 핀이 같은 이름으로 뭉친다.

```
LP-G × 3    LP_GPIO0 / LP_GPIO1 / LP_GPIO2
SDIO × 3    SDIO_DATA1 / SDIO_DATA2 / SDIO_DATA3
LP-I × 2 · BAT × 2 · GND_ × 2
```

### 실크 라벨 → GPIO

| 실크 | GPIO | 부가 기능 | 넷리스트에서 잘린 이름 |
|---|---|---|---|
| D0 | GPIO0 | LP_GPIO0 · ADC | `LP-G` |
| D1 | GPIO1 | LP_GPIO1 · ADC | `LP-G` |
| D2 | GPIO2 | LP_GPIO2 · ADC | `LP-G` |
| D3 | GPIO21 | SDIO_DATA1 | `SDIO` |
| D4 | GPIO22 | SDIO_DATA2 · I2C SDA | `SDIO` |
| D5 | GPIO23 | SDIO_DATA3 · I2C SCL | `SDIO` |
| D6 | GPIO16 | UART TX | `GPIO` |
| D7 | GPIO17 | UART RX | `D7_R` |
| D8 | GPIO19 | SPI SCK | `D8_S` |
| D9 | GPIO20 | SPI MISO | `D9_M` |
| D10 | GPIO18 | SPI MOSI | `D10_` |

출처: [XIAO ESP32C6 — Seeed Studio Wiki](https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/)

### 같은 이름을 좌표로 구분한다

헤더는 두 열이고 피치는 1000 (0.1 inch) 이다. Y 내림차순이 실크 순서다.

| Y | X=-2635 (왼쪽) | 실크 | X=3365 (오른쪽) | 실크 |
|---:|---|---|---|---|
| 7922 | `LP-G` | D0 | `5V` | 5V |
| 6922 | `LP-G` | D1 | `GND` | GND |
| 5922 | `LP-G` | **D2** | `3V3` | 3V3 |
| 4922 | `SDIO` | D3 | `D10_` | D10 |
| 3922 | `SDIO` | D4 | `D9_M` | D9 |
| 2922 | `SDIO` | **D5** | `D8_S` | D8 |
| 1922 | `GPIO` | D6 | `D7_R` | D7 |

**오른쪽 열이 XIAO 표준 배치와 7/7 일치**하므로 왼쪽 열은 D0~D6 순서다.
절단 패턴(`LP-G`×3 · `SDIO`×3 · `GPIO`)도 위 표에서 독립적으로 같은 답이 나온다.

> ### ✅ 확정됨 (2026.08.17, 하드웨어 담당 한지양)
>
> 좌표 추론이 **정확히 맞았다.** 담당자 답변과 손그림 회로도로 확정:
>
> | | 담당자 답변 | 우리 추론 |
> |---|---|---|
> | mmWave 센서 OUT | **D2** ("Mmwave 3번out이 Esp d2로 드감") | D2 ✅ |
> | 릴레이 제어선 | **D5** ("릴레이 d5") | D5 ✅ |
>
> 좌표만으로 4자 절단을 되돌릴 수 있다는 것이 실증됐다.
> 아래 표를 그대로 모듈 핀아웃 DB에 넣어도 된다.

### K1 릴레이 모듈 — 같은 방법으로 6패드를 분리했다

K1 의 패드는 **6개가 전부 `pad-`** 로 잘린다. X 좌표가 두 덩어리로 갈린다.

| X | Y | 네트 | 정체 |
|---|---:|---|---|
| **-2785** (제어부) | -1401 | `_IN_ACTIVE_LOW` | **IN** |
| | -2401 | `GND_BUS` | GND |
| | -3401 | `5V_BUS` | VCC |
| **11585** (스위치부) | -433 | `D_POS_SWITCHED` | **NO** → LED 커넥터 J2 |
| | -2401 | `5V_BUS` | COM |
| | -4370 | `N/C` | NC (미사용) |

손그림 회로도와 **6핀 전부 일치한다** — "NC 사용X" 까지 맞다.
X 좌표 클러스터링이 실제로 제어부/스위치부를 갈라낸다는 증거다.

### 파서에 필요한 것

이름만으로는 D3 · D4 · D5 를 구분할 수 없으므로, 좌표 클러스터링으로 패드마다
실크 라벨과 GPIO 번호를 확정해야 한다. 그게 없으면 R1 · R5 · R7 · R8 이
**우리 보드에서 전부 못 돈다.** 지금 도는 R11 · R12 는 전원 도메인만 보기 때문에
핀 번호가 필요 없었을 뿐이다.

```jsonc
{
  "XIAO-ESP32C6": {
    "chip": "esp32c6",
    "pins": { "D0": 0, "D1": 1, "D2": 2, "D3": 21, "D4": 22, "D5": 23,
              "D6": 16, "D7": 17, "D8": 19, "D9": 20, "D10": 18 }
  }
}
```

실제 대조 사례는
[`apps/api/tests/fixtures/esp32-c6-presence-smart-light.EXPECTED.md`](../apps/api/tests/fixtures/esp32-c6-presence-smart-light.EXPECTED.md)
에 있다.

---

## 근거

- [ESP32-C6 Datasheet — Espressif](https://documentation.espressif.com/esp32-c6_datasheet_en.html)
- [GPIO & RTC GPIO — ESP32-C6, ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c6/api-reference/peripherals/gpio.html)
- [ESP32 Datasheet — Espressif](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf) (U0TXD = GPIO1)
- [UART — ESP32-C6, ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c6/api-reference/peripherals/uart.html) (U0TXD 기본 핀)
- [Boot Mode Selection — ESP32-C6, esptool](https://docs.espressif.com/projects/esptool/en/latest/esp32c6/advanced-topics/boot-mode-selection.html)
- [ADC2 / WiFi 충돌 — ESP-IDF](https://github.com/espressif/esp-idf/blob/v4.0.3/docs/en/api-reference/peripherals/adc.rst)
- [XIAO ESP32C6 핀아웃 — Seeed Studio Wiki](https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/)

표를 고칠 때는 **근거 링크를 함께 남깁니다.** 출처 없는 핀 번호는 규칙에 넣지 않습니다.
