"""칩 제약과 모듈 핀아웃 — `docs/CHIPS.md` 의 코드 사본.

**표가 진실이고 여기는 사본이다.** 값을 여기서 바꾸지 않는다.
핀 번호를 규칙 안에 적지 않기 위해 존재한다 (CLAUDE.md 3절 · README 설계원칙 5).

표에 해당 항목이 없으면 규칙은 "이상 없음"이 아니라 `skipped` 를 낸다.
근거 출처는 `docs/CHIPS.md` 하단 링크 목록에 있다. 출처 없는 핀 번호는 넣지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Chip:
    """칩 하나의 핀 제약."""

    id: str
    name: str
    #: OUTPUT 으로 설정할 수 없는 핀
    input_only: tuple[int, ...] = ()
    #: 내장 플래시 전용
    spi_flash: tuple[int, ...] = ()
    #: 부팅 시 레벨이 부팅 모드를 결정하는 핀
    strapping: tuple[int, ...] = ()
    #: 이 칩의 **IO 로직 전압**. 데이터시트가 정하는 값이고 배선으로 안 바뀐다.
    #:
    #: 넷리스트만으로는 이걸 알 수 없다. 개발보드는 `5V` 핀과 `3V3` 핀을 둘 다 뽑는데
    #: 하나는 레귤레이터 **입력**이고 하나는 **출력**이라, 아무거나 고르면 절반은 틀린다.
    #: 실제로 우리 보드의 XIAO 가 REV2 에서 3V3 핀을 떼자 5V 부품으로 판정됐다.
    logic_volts: float | None = None
    adc1: tuple[int, ...] = ()
    #: 비어 있으면 이 칩에 ADC2 가 없다는 뜻이다 (없음 ≠ 이상 없음)
    adc2: tuple[int, ...] = ()
    #: 부팅·리셋 순간에 **칩이 스스로** 신호를 내보내는 핀.
    #: 코드가 돌기 전이라 펌웨어로는 막을 수 없다. 비어 있으면 "이 칩은 출처를 못 찾았다"
    #: 는 뜻이지 "그런 핀이 없다"가 아니다 — 규칙은 비면 아무 말도 하지 않는다.
    boot_output: tuple[int, ...] = ()
    #: 그중 부팅 로그(UART0 TX)가 나가는 핀. `boot_output` 의 부분집합이다.
    #: 사유 문구가 달라서 따로 둔다 — 로그는 수백 밀리초 동안 계속 토글한다.
    boot_log_tx: int | None = None
    #: 내장 USB(Serial/JTAG)가 쓰는 데이터 핀 (D-, D+).
    #: **코드가 `pinMode` 로 안 만지는 것이 정상이다** — 주변장치가 직접 몬다.
    #: 만지면 오히려 USB 가 죽는다. R08 이 이 핀을 "초기화 안 함" 으로 잡으면 오탐이다.
    #: 비어 있으면 **그 칩에 내장 USB 가 없다는 뜻**이다 (구형 ESP32 가 그렇다) —
    #: `boot_output` 의 빈 값과 의미가 다르다. 칩마다 주석으로 밝힌다.
    usb: tuple[int, ...] = ()


ESP32 = Chip(
    id="esp32",
    name="ESP32 (구형, ESP32-D0WD 계열)",
    input_only=(34, 35, 36, 37, 38, 39),
    # ESP32 데이터시트 Recommended Operating Conditions: VDD 3.0~3.6V (typ 3.3V).
    # 5V 를 받는 개발보드도 칩은 3.3V 로 돈다 — 보드의 5V 핀은 레귤레이터 입력이다.
    logic_volts=3.3,
    spi_flash=tuple(range(6, 12)),
    strapping=(0, 2, 5, 12, 15),
    adc1=tuple(range(32, 40)),
    adc2=(0, 2, 4, 12, 13, 14, 15, 25, 26, 27),
    # GPIO1 은 부팅 로그(U0TXD), 나머지는 부팅·리셋 순간 HIGH 또는 PWM 이 나온다.
    # 플래시 핀(6~11)도 부팅 때 토글하지만 그건 R02 가 배선 자체를 잡는다.
    boot_output=(0, 1, 3, 5, 14, 15),
    boot_log_tx=1,
    usb=(),  # 구형 ESP32 에는 내장 USB 가 **없다.** 외부 USB-UART 브리지를 쓴다
)

ESP32C6 = Chip(
    id="esp32c6",
    name="ESP32-C6",
    input_only=(),  # C6 는 입력 전용 핀이 없다
    # ESP32-C6 데이터시트 Table 5-2: VDDA/VDDPST 3.0~3.6V (typ 3.3V).
    # `parts/esp32-c6.json` 의 vcc_nominal 과 같은 값이고 출처도 같다.
    logic_volts=3.3,
    spi_flash=tuple(range(24, 31)),
    strapping=(4, 5, 8, 9, 15),
    adc1=tuple(range(0, 7)),
    adc2=(),  # 칩에 ADC2 가 존재하지 않는다
    # C6 는 U0TXD(GPIO16)만 출처가 확실하다. 부팅 글리치 핀 목록은 공식 문서에서
    # 못 찾았다 — **없어서 비운 게 아니라 못 찾아서 비웠다.** 지어내지 않는다.
    boot_output=(16,),
    boot_log_tx=16,
    usb=(12, 13),  # USB Serial/JTAG. ESP-IDF: "GPIO12 and GPIO13 are used by USB-JTAG by default"
)

ESP32S3 = Chip(
    id="esp32s3",
    name="ESP32-S3",
    input_only=(),  # S3 는 입력 전용 핀이 없다 — 모든 GPIO 가 양방향
    # ESP32-S3 데이터시트 Recommended Operating Conditions: VDD 3.0~3.6V (typ 3.3V).
    # C6·C3 와 같은 이유로 넣는다 — 빠져 있어서 S3 보드의 도메인 추론이 배선에만 기댔다.
    logic_volts=3.3,
    # 내장 플래시·PSRAM 전용. **옥타 플래시 핀 GPIO33~37 은 일부러 뺐다** —
    # 옥타를 쓰는 보드에만 해당하는데, 표에 넣으면 쿼드 보드에서 R02 가 오탐을 낸다.
    spi_flash=tuple(range(26, 33)),
    strapping=(0, 3, 45, 46),
    adc1=tuple(range(1, 11)),
    adc2=tuple(range(11, 21)),  # WiFi 구동 중 사용 불가
    # C6 와 같다 — U0TXD(GPIO43)만 출처가 확실하다. 부팅 글리치 핀 목록은
    # 공식 문서에서 못 찾았다. **없어서 비운 게 아니라 못 찾아서 비웠다.**
    boot_output=(43,),
    boot_log_tx=43,
    # USB Serial/JTAG. ESP-IDF: "GPIO19 and GPIO20 are used by USB-JTAG by default".
    # **ADC2 채널과 겹친다** — 아날로그로 쓰면 USB 가 죽는다.
    usb=(19, 20),
)

ESP32C3 = Chip(
    id="esp32c3",
    name="ESP32-C3",
    input_only=(),  # C3 는 입력 전용 핀이 없다
    # ESP32-C3 데이터시트 Recommended Operating Conditions: VDD 3.0~3.6V.
    logic_volts=3.3,
    # **GPIO12·13 을 일부러 뺐다.** ESP-IDF 는 "GPIO12 ~ GPIO17 are **usually** used
    # for SPI flash" 라고 쓰는데, 그 "usually" 가 이 두 핀이다 —
    # GPIO12=SPIHD · GPIO13=SPIWP 는 **쿼드(QIO) 모드에서만** 쓰인다.
    # 2선(DIO) 모드로 플래시를 다는 보드에서는 남는 GPIO 다.
    #
    # 넣었다가 실측에서 바로 데였다. LuatOS CORE-ESP32-C3 가 DIO 모드라 그 둘을
    # LED 로 뽑아 쓰는데, 우리가 "부팅이 실패한다" 고 치명 3건을 냈다 — **전부 오탐**이다.
    # 넷리스트는 플래시 모드를 말해 주지 않으므로 우리는 모른다 (헌법 2-2).
    #
    # 남긴 넷은 모드와 무관하게 항상 플래시다 —
    # GPIO14=SPICS0 · GPIO15=SPICLK · GPIO16=SPID · GPIO17=SPIQ (데이터시트 Table 2-4).
    spi_flash=(14, 15, 16, 17),
    strapping=(2, 8, 9),  # ESP-IDF: "GPIO2, GPIO8 and GPIO9 are strapping pins."
    adc1=(0, 1, 2, 3, 4),  # 데이터시트 Table 2-6: ADC1_CH0~CH4
    adc2=(5,),             # 같은 표: ADC2_CH0 = GPIO5
    # 데이터시트 Table 2-4 에서 U0TXD = GPIO21. **다른 부팅 글리치 핀은 못 찾았다** —
    # C6·S3 와 같다. 없어서 비운 게 아니라 출처를 못 찾아서 비웠다.
    boot_output=(21,),
    boot_log_tx=21,
    # ESP-IDF: "GPIO18 and GPIO19 are used by USB-JTAG by default."
    usb=(18, 19),
)

ESP32H2 = Chip(
    id="esp32h2",
    name="ESP32-H2",
    input_only=(),  # H2 도 입력 전용 핀이 없다
    logic_volts=3.3,
    # ESP-IDF GPIO 문서: "GPIO15-21 are usually used for SPI flash and not
    # recommended for other uses." 같은 문서가 GPIO15~21 과 GPIO6~7 은 외부 핀으로
    # 나오지 않는다고 밝힌다 — 회로도에 안 보이는 것이 정상이다.
    spi_flash=tuple(range(15, 22)),
    # ESP-IDF: "GPIO2, GPIO3, GPIO8, GPIO9, and GPIO25 are strapping pins."
    strapping=(2, 3, 8, 9, 25),
    adc1=(1, 2, 3, 4, 5),  # 데이터시트: ADC1_CH0~CH4 = GPIO1~5
    adc2=(),               # 데이터시트에 ADC2 가 없다 ("up to five channels")
    boot_output=(24,),     # 데이터시트: U0TXD = GPIO24. 나머지는 못 찾았다
    boot_log_tx=24,
    # ESP-IDF: "GPIO 26 and 27 are used by USB-Serial-JTAG by default."
    usb=(26, 27),
)

RP2040 = Chip(
    id="rp2040",
    name="RP2040",
    #: **이 칩은 우리 표의 칸 대부분이 진짜로 비어 있다.** 못 찾아서가 아니다.
    #: ESP32 는 플래시·USB·스트래핑이 전부 일반 GPIO 를 빌려 쓰는데,
    #: RP2040 은 그것들을 **따로 뽑아 놨다.** 그래서 GPIO 를 쓰다가 밟을 지뢰가 적다.
    #: 이 빈칸들은 「이 보드는 그 위험이 없다」는 뜻이고, 규칙은 조용히 넘어가는 게 맞다.
    input_only=(),  # 모든 GPIO 가 양방향
    logic_volts=3.3,  # 데이터시트: IOVDD 1.8~3.3V, 보드는 관례적으로 3.3V
    # QSPI 플래시는 **별도 뱅크**다 (QSPI_SD0~3 · SCLK · SS). GPIO0~29 와 번호가
    # 겹치지 않으므로 R02 가 볼 것이 없다. ESP32 처럼 GPIO 를 뺏기지 않는다.
    spi_flash=(),
    # 스트래핑 핀이 없다. 부팅 모드는 BOOTSEL 버튼(QSPI CS)으로 고르고 GPIO 가 아니다.
    strapping=(),
    adc1=(26, 27, 28, 29),  # 데이터시트: GPIO26~29 가 ADC 입력
    adc2=(),                # ADC 가 하나뿐이다 (멀티플렉서로 채널을 고른다)
    # 부트롬이 UART 로 로그를 뿌리지 않는다 (USB 대용량저장으로 올라온다).
    # 부팅 순간 GPIO 를 구동한다는 1차 출처를 못 찾았다 — 지어내지 않는다.
    boot_output=(),
    # USB 는 전용 핀(USB_DP · USB_DM)이라 GPIO 와 안 겹친다. ESP32 와 다른 이유의 빈칸이다.
    usb=(),
)

CHIPS: dict[str, Chip] = {
    c.id: c for c in (ESP32, ESP32C3, ESP32C6, ESP32H2, ESP32S3, RP2040)
}


#: 개발보드 이름 → 그 위에 얹힌 칩.
#:
#: 회로도는 칩 이름을 안 적고 **보드 이름을 적는다.** 실측 28개 보드에서 RP2040 계열
#: 6개가 전부 `Pico` · `RaspberryPi_Pico` 라고만 적혀 있었다.
#:
#: **부분일치로 하면 안 된다.** `Pico 2` 는 RP2040 이 아니라 **RP2350** 이고,
#: 그건 우리 표에 없는 칩이다. `pico` 가 `pico2` 에 걸리면 다른 칩의 핀 제약으로
#: 판정하게 되는데, 그건 못 잡는 것보다 나쁘다. 그래서 **정규화 후 정확히 같을 때만**
#: 인정한다. 모르는 보드는 모르는 채로 둔다 (헌법 2-2).
#:
#: 출처: https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html
#: — Pico · Pico H · Pico W · Pico WH = RP2040 / Pico 2 계열 = RP2350
BOARD_TO_CHIP: dict[str, str] = {
    "pico": "rp2040",
    "picoh": "rp2040",
    "picow": "rp2040",
    "picowh": "rp2040",
    "raspberrypipico": "rp2040",
    "raspberrypipicoh": "rp2040",
    "raspberrypipicow": "rp2040",
    "raspberrypipicowh": "rp2040",
}


# --------------------------------------------------------------------- 모듈

@dataclass(frozen=True)
class HeaderPin:
    """모듈 헤더의 패드 하나.

    `token` 은 IPC-D-356 이 4자로 자른 뒤 실제로 나오는 이름이다.
    Seeed 문서의 이름에서 유추하지 않고, 실측한 값을 적는다.
    """

    silk: str
    gpio: int | None
    token: str


@dataclass(frozen=True)
class ModulePinout:
    """모듈 하나. 헤더 열마다 위(Y 큰 쪽)에서 아래 순서로 적는다."""

    id: str
    chip: str
    source: str
    columns: tuple[tuple[HeaderPin, ...], ...] = field(default_factory=tuple)

    def signature(self, column_index: int) -> tuple[str, ...]:
        """그 열이 넷리스트에서 어떤 이름 나열로 보여야 하는지."""
        return tuple(p.token for p in self.columns[column_index])

    @property
    def silk_to_gpio(self) -> dict[str, int]:
        return {
            p.silk: p.gpio
            for col in self.columns
            for p in col
            if p.gpio is not None
        }

    @property
    def gpio_to_silk(self) -> dict[int, str]:
        return {g: s for s, g in self.silk_to_gpio.items()}


#: Seeed Studio XIAO ESP32-C6.
#: 좌표 근거와 검증 과정은 docs/CHIPS.md 「모듈 핀아웃」 절과
#: tests/fixtures/esp32-c6-presence-smart-light.EXPECTED.md 1절에 있다.
#: 하드웨어 담당(한지양·권지효) 실물 실크 대조 대기 중.
XIAO_ESP32C6 = ModulePinout(
    id="XIAO-ESP32C6",
    chip="esp32c6",
    source="https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/",
    columns=(
        (
            HeaderPin("D0", 0, "LP-G"),
            HeaderPin("D1", 1, "LP-G"),
            HeaderPin("D2", 2, "LP-G"),
            HeaderPin("D3", 21, "SDIO"),
            HeaderPin("D4", 22, "SDIO"),
            HeaderPin("D5", 23, "SDIO"),
            HeaderPin("D6", 16, "GPIO"),
        ),
        (
            HeaderPin("5V", None, "5V"),
            HeaderPin("GND", None, "GND"),
            HeaderPin("3V3", None, "3V3"),
            HeaderPin("D10", 18, "D10_"),
            HeaderPin("D9", 20, "D9_M"),
            HeaderPin("D8", 19, "D8_S"),
            HeaderPin("D7", 17, "D7_R"),
        ),
    ),
)

MODULES: dict[str, ModulePinout] = {m.id: m for m in (XIAO_ESP32C6,)}
