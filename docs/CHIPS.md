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
| 부팅 시 출력 | GPIO0, 1, 3, 5, 14, 15 | 리셋 직후 HIGH 또는 PWM 이 나온다. **GPIO1 은 부팅 로그(U0TXD)** |

## ESP32-C6

| 분류 | 핀 | 의미 |
|---|---|---|
| 입력 전용 | **없음** | GPIO0~30 전부 양방향 |
| SPI 플래시 | GPIO24 ~ GPIO30 | 내장 플래시 전용. 다른 용도 비권장 |
| 스트래핑 | GPIO4, 5, 8, 9, 15 | GPIO8·9는 부팅 모드, GPIO15는 JTAG 소스 선택 |
| ADC1 | GPIO0 ~ GPIO6 | 7채널 |
| ADC2 | **없음** | 칩에 ADC2가 존재하지 않음 |
| 부팅 시 출력 | GPIO16 | U0TXD. 부트 ROM 로그가 **115200bps** 로 나간다 |

> **C6 의 부팅 시 출력 목록은 GPIO16 하나뿐입니다 — 출처를 찾은 것이 그것뿐이라서입니다.**
> 구형 ESP32 처럼 부팅 때 PWM 이 나오는 핀 목록을 Espressif 공식 문서에서 찾지 못했습니다.
> **"그런 핀이 없다"가 아니라 "아직 못 찾았다"** 입니다. 출처를 찾으면 여기에 추가하세요.
> 지어낸 핀 번호를 넣으면 R09 가 그 보드에서 오탐을 냅니다.

### C6에서 주의할 겹침

ADC 채널(GPIO0~6)과 스트래핑 핀(GPIO4, 5)이 **겹칩니다.**
GPIO4·5를 아날로그 입력으로 쓰면 부팅 시점의 레벨이 부팅 모드에 영향을 줄 수 있습니다.

---

## ESP32-S3

**2026-08-20 추가.** 한지양이 카메라 센서(OV3660)로 바꾸면서 보드를 S3 로 옮겼습니다.
OV3660 은 병렬(DVP) 카메라라 C6 로는 못 받습니다 — S3 에는 LCD_CAM 이 있습니다.

| 분류 | 핀 | 의미 |
|---|---|---|
| 입력 전용 | **없음** | 모든 GPIO 가 양방향 |
| SPI 플래시 | GPIO26 ~ GPIO32 | 내장 플래시·PSRAM 전용. 다른 용도 비권장 |
| 스트래핑 | GPIO0, 3, 45, 46 | GPIO0·46 이 부팅 모드를 정한다 |
| ADC1 | GPIO1 ~ GPIO10 | 10채널 |
| ADC2 | GPIO11 ~ GPIO20 | **WiFi 구동 중 사용 불가** |
| 부팅 시 출력 | GPIO43 | U0TXD. 부트 ROM 로그가 **115200bps** 로 나간다 |

> **옥타 플래시 핀 GPIO33~37 은 일부러 뺐습니다.**
> ESP-IDF 는 "Octal flash 또는 PSRAM 을 쓰면 GPIO33~37 이 SPIIO4~SPIIO7·SPIDQS 에
> 연결되어 다른 용도로 권장되지 않는다" 고 적습니다 — **일부 보드에만 해당합니다.**
> 표에 넣으면 쿼드 플래시 보드에서 R02 가 오탐을 냅니다 (헌법 2-3).
> 보드가 옥타인지 확인되면 그때 넣습니다.

> **S3 의 부팅 시 출력 목록도 GPIO43 하나뿐입니다** — C6 와 같은 이유입니다.
> 구형 ESP32 처럼 부팅 때 PWM 이 나오는 핀 목록을 공식 문서에서 찾지 못했습니다.
> **"그런 핀이 없다"가 아니라 "아직 못 찾았다"** 입니다.

### S3에서 주의할 겹침

1. **ADC2(GPIO11~20)와 USB-JTAG(GPIO19, 20)이 겹칩니다.**
   ESP-IDF 는 GPIO19·20 이 기본으로 USB-JTAG 에 쓰이고 다시 설정하면 그 기능이
   꺼진다고 적습니다. GPIO19·20 을 아날로그 입력으로 쓰면 USB 가 죽습니다.
   **코드 표에 넣었습니다** (`Chip.usb`, 8/20) — C6 는 GPIO12·13, 구형 ESP32 는
   내장 USB 가 **없습니다**(외부 USB-UART 브리지를 씁니다).
   R08 이 이 핀을 "코드가 초기화 안 함" 으로 잡지 않습니다 — 주변장치가 직접 몹니다.
2. **스트래핑 GPIO3 이 ADC1 채널과 겹칩니다.** GPIO3 을 아날로그 입력으로 쓰면
   부팅 시점 레벨이 부팅 모드에 영향을 줄 수 있습니다.

---

## ESP32-C3

| 분류 | 핀 | 의미 |
|---|---|---|
| 입력 전용 | **없음** | 모든 GPIO 가 양방향 |
| SPI 플래시 | GPIO14 ~ GPIO17 | SPICS0 · SPICLK · SPID · SPIQ — **모드와 무관하게 항상 플래시** |
| ~~GPIO12 · 13~~ | **일부러 뺐다** | SPIHD · SPIWP 는 **쿼드(QIO) 모드에서만** 쓴다 |
| 스트래핑 | GPIO2, 8, 9 | ESP-IDF: "GPIO2, GPIO8 and GPIO9 are strapping pins" |
| ADC1 | GPIO0 ~ GPIO4 | 데이터시트 Table 2-6, ADC1_CH0~CH4 |
| ADC2 | GPIO5 | 같은 표, ADC2_CH0 하나뿐 |
| USB Serial/JTAG | GPIO18, 19 | ESP-IDF: "used by USB-JTAG by default" |
| 부팅 시 출력 | GPIO21 | U0TXD (데이터시트 Table 2-4). ROM 로그 115200bps |

> **GPIO12·13 을 넣었다가 실측에서 바로 데였습니다.** ESP-IDF 는 "GPIO12 ~ GPIO17 are
> **usually** used for SPI flash" 라고 쓰는데, 그 "usually" 가 이 두 핀입니다.
> LuatOS CORE-ESP32-C3 는 2선(DIO) 모드라 그 둘을 LED 로 뽑아 쓰는데,
> 우리가 "부팅이 실패한다" 고 치명 3건을 냈습니다 — **전부 오탐**이었습니다.
> 넷리스트는 플래시 모드를 말해 주지 않으므로 우리는 모릅니다 (헌법 2-2).
>
> C6·S3 와 같습니다 — **부팅 글리치 핀 목록은 아직 못 찾았습니다.** 없어서가 아닙니다.

---

## ESP32-H2

| 분류 | 핀 | 의미 |
|---|---|---|
| 입력 전용 | **없음** | 모든 GPIO 가 양방향 |
| SPI 플래시 | GPIO15 ~ GPIO21 | ESP-IDF: "usually used for SPI flash and not recommended for other uses" |
| 스트래핑 | GPIO2, 3, 8, 9, 25 | ESP-IDF 원문 그대로 |
| ADC1 | GPIO1 ~ GPIO5 | 데이터시트 ADC1_CH0~CH4 |
| ADC2 | **없음** | 데이터시트가 "up to five channels" 로 하나만 말합니다 |
| USB Serial/JTAG | GPIO26, 27 | ESP-IDF: "used by USB-Serial-JTAG by default" |
| 부팅 시 출력 | GPIO24 | U0TXD (데이터시트) |

> ESP-IDF 가 밝힙니다 — **GPIO15~21 과 GPIO6~7 은 외부 핀으로 나오지 않습니다.**
> 회로도에 그 번호가 안 보이는 것이 정상입니다.

---

## RP2040

**이 칩은 우리 표의 칸 대부분이 진짜로 비어 있습니다. 못 찾아서가 아닙니다.**

| 분류 | 핀 | 의미 |
|---|---|---|
| 입력 전용 | **없음** | 모든 GPIO 가 양방향 |
| SPI 플래시 | **해당 없음** | QSPI 가 **별도 뱅크**입니다. GPIO0~29 와 번호가 안 겹칩니다 |
| 스트래핑 | **없음** | 부팅 모드는 BOOTSEL 버튼(QSPI CS)이고 GPIO 가 아닙니다 |
| ADC | GPIO26 ~ GPIO29 | ADC 가 하나뿐이고 멀티플렉서로 채널을 고릅니다 |
| USB | **해당 없음** | USB_DP · USB_DM 이 전용 핀입니다 |
| 부팅 시 출력 | **못 찾음** | 부트롬이 UART 로그를 안 뿌립니다 (USB 대용량저장으로 올라옵니다) |

> ESP32 는 플래시·USB·스트래핑이 전부 일반 GPIO 를 빌려 씁니다. RP2040 은 그것들을
> **따로 뽑아 놨습니다.** 그래서 GPIO 를 쓰다 밟을 지뢰가 적습니다.
> 이 빈칸들은 「이 보드는 그 위험이 없다」는 뜻이고, 규칙이 조용한 것이 정답입니다.

---

## 개발보드 이름 → 칩

회로도는 칩 이름을 안 적고 **보드 이름을 적습니다.** 실측 28개 보드에서 RP2040 계열
6개가 전부 `Pico` · `RaspberryPi_Pico` 라고만 적혀 있었습니다.

| 보드 값 (정규화) | 칩 |
|---|---|
| `pico` · `picoh` · `picow` · `picowh` | RP2040 |
| `raspberrypipico` (+ `h` · `w` · `wh`) | RP2040 |

**부분일치로 하면 안 됩니다.** `Pico 2` 는 RP2040 이 아니라 **RP2350** 이고 우리 표에
없는 칩입니다. `pico` 가 `pico2` 에 걸리면 다른 칩의 핀 제약으로 판정하게 되는데,
그건 못 잡는 것보다 나쁩니다. 그래서 **정규화 후 정확히 같을 때만** 인정합니다.

---

## 규칙이 칩별로 어떻게 갈리나

| 규칙 | ESP32 (구형) | ESP32-C6 |
|---|---|---|
| **R1** 코드가 쓸 수 없는 핀을 사용 | 입력 전용 핀에 OUTPUT → `CRITICAL` | 플래시 핀 사용 → `CRITICAL`<br>스트래핑 핀 사용 → `WARNING` |
| **R2** 회로도가 플래시 핀에 배선 | GPIO6~11 배선 → `CRITICAL` | GPIO24~30 배선 → `CRITICAL` |
| **R3** 스트래핑 핀이 전원·접지 직결 | GPIO0·2·5·12·15 → `WARNING` | GPIO4·5·8·9·15 → `WARNING` |
| **R5** 칩이 지원하지 않는 조합 | ADC2 + WiFi 동시 → `CRITICAL` | ADC2 없음 → `skipped`<br>ADC(GPIO4·5) + 스트래핑 겹침 → `WARNING` |
| **R9** 부팅 시 출력 핀에 부하 | GPIO0·1·3·5·14·15 에 구동 부품 → `WARNING` | GPIO16(U0TXD)에 구동 부품 → `WARNING` |
| **R7·R8·R10** 코드 ↔ 회로도 대조 | 칩 무관 | 칩 무관 |

**R2·R3 은 회로도만 봅니다.** R1 이 같은 핀을 코드 쪽에서 보는 것과 짝입니다 —
코드가 안 써도 배선 자체가 문제인 경우를 R2·R3 이 잡습니다.

두 규칙 모두 **오탐 경계를 좁게 잡았습니다.**
- R2 는 플래시 핀 여러 가닥이 한 부품으로 모이면 그것을 플래시 IC 로 보고 넘어갑니다.
  맨칩 설계에서 외부 플래시로 가는 배선은 정상이기 때문입니다.
- R3 은 **직결만** 잡습니다. 저항·스위치를 거치면 패드가 다른 네트에 있어 안 걸립니다.
  풀업 저항과 부트 버튼은 정상 설계입니다.
- R9 는 **구동 부품(K·Q·M·BZ·LS)만** 부하로 셉니다. 커넥터(`J`)로 빼는 것은
  시리얼 콘솔이라 정상 설계이고, 그것까지 잡으면 거의 모든 개발보드에서 오탐이 납니다.
  레일에 직결된 경우는 R3 이 보므로 R9 는 비켜섭니다 — 같은 배선을 두 번 읽히지 않습니다.

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
- [Boot Mode Selection — ESP32-C6, esptool](https://docs.espressif.com/projects/esptool/en/latest/esp32c6/advanced-topics/boot-mode-selection.html)
- [ADC2 / WiFi 충돌 — ESP-IDF](https://github.com/espressif/esp-idf/blob/v4.0.3/docs/en/api-reference/peripherals/adc.rst)
- 부팅 시 출력 (ESP32-C6, GPIO16 = U0TXD 기본 시리얼 콘솔):
  [ESP32-C6-DevKitC-1 핀아웃](https://www.espboards.dev/esp32/esp32-c6-devkitc-1/) ·
  ROM 로그 115200bps 는 [Boot Mode Selection — ESP32-C6, esptool](https://docs.espressif.com/projects/esptool/en/latest/esp32c6/advanced-topics/boot-mode-selection.html)
- 부팅 시 출력 (구형 ESP32, GPIO0·1·3·5·14·15):
  [ESP32 Pinout Reference — Random Nerd Tutorials](https://randomnerdtutorials.com/esp32-pinout-reference-gpios/)
  (2차 출처입니다. **1차 출처로 교체해 주세요** — 하드웨어 담당 검수 항목)
- [XIAO ESP32C6 핀아웃 — Seeed Studio Wiki](https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/)

**ESP32-S3** (2026-08-20 확인, 전부 1차 출처):
- [GPIO & RTC GPIO — ESP32-S3, ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/gpio.html)
  — 스트래핑 GPIO0·3·45·46 · SPI 플래시 GPIO26~32 · 옥타 GPIO33~37 · 입력 전용 없음 · USB-JTAG GPIO19·20
- [Boot Mode Selection — ESP32-S3, esptool](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/advanced-topics/boot-mode-selection.html)
  — GPIO0 Low 로 시리얼 부트로더 진입 · GPIO46 은 floating 또는 Low · ROM 로그 115200bps
- [ESP32-S3 Datasheet — Espressif](https://documentation.espressif.com/esp32-s3_datasheet_en.html) — U0TXD = GPIO43
- [adc_channel.h — esp-idf/components/soc/esp32s3](https://github.com/espressif/esp-idf/blob/release/v5.3/components/soc/esp32s3/include/soc/adc_channel.h)
  — ADC1 = GPIO1~10 · ADC2 = GPIO11~20 (헤더 정의를 그대로 읽었습니다)
- [ADC Oneshot — ESP32-S3, ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/adc/adc_oneshot.html)
  — "ADC2 is also used by Wi-Fi"

**ESP32-C3** (2026-08-24 확인, 전부 1차 출처):
- [GPIO & RTC GPIO — ESP32-C3, ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-reference/peripherals/gpio.html)
  — 스트래핑 GPIO2·8·9 · SPI 플래시 GPIO12~17 · 입력 전용 없음 · USB-JTAG GPIO18·19
- [Boot Mode Selection — ESP32-C3, esptool](https://docs.espressif.com/projects/esptool/en/latest/esp32c3/advanced-topics/boot-mode-selection.html)
  — GPIO9 Low 로 시리얼 부트로더 진입 · ROM 로그 115200bps
- [ESP32-C3 Datasheet — Espressif](https://documentation.espressif.com/esp32-c3_datasheet_en.html)
  — Table 2-4 U0TXD = GPIO21 · Table 2-6 ADC1_CH0~CH4 = GPIO0~4 · ADC2_CH0 = GPIO5

**ESP32-H2** (2026-08-24 확인, 전부 1차 출처):
- [GPIO & RTC GPIO — ESP32-H2, ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/stable/esp32h2/api-reference/peripherals/gpio.html)
  — 스트래핑 GPIO2·3·8·9·25 · SPI 플래시 GPIO15~21 · USB-Serial-JTAG GPIO26·27 ·
  GPIO15~21 과 GPIO6~7 은 외부 핀으로 안 나옴
- [ESP32-H2 Datasheet — Espressif](https://documentation.espressif.com/esp32-h2_datasheet_en.html)
  — U0TXD = GPIO24 · ADC1_CH0~CH4 = GPIO1~5 · ADC2 없음

**RP2040** (2026-08-24 확인, 전부 1차 출처):
- [RP2040 Datasheet — Raspberry Pi](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf)
  — QSPI 는 별도 뱅크 · GPIO26~29 가 ADC 입력 · USB_DP/USB_DM 전용 핀 · 입력 전용 없음
- [Raspberry Pi Pico series — Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html)
  — Pico · Pico H · Pico W · Pico WH = **RP2040** / Pico 2 계열 = **RP2350**(우리 표에 없음)

표를 고칠 때는 **근거 링크를 함께 남깁니다.** 출처 없는 핀 번호는 규칙에 넣지 않습니다.
