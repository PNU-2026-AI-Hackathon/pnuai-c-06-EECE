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


ESP32 = Chip(
    id="esp32",
    name="ESP32 (구형, ESP32-D0WD 계열)",
    input_only=(34, 35, 36, 37, 38, 39),
    spi_flash=tuple(range(6, 12)),
    strapping=(0, 2, 5, 12, 15),
    adc1=tuple(range(32, 40)),
    adc2=(0, 2, 4, 12, 13, 14, 15, 25, 26, 27),
    # GPIO1 은 부팅 로그(U0TXD), 나머지는 부팅·리셋 순간 HIGH 또는 PWM 이 나온다.
    # 플래시 핀(6~11)도 부팅 때 토글하지만 그건 R02 가 배선 자체를 잡는다.
    boot_output=(0, 1, 3, 5, 14, 15),
    boot_log_tx=1,
)

ESP32C6 = Chip(
    id="esp32c6",
    name="ESP32-C6",
    input_only=(),  # C6 는 입력 전용 핀이 없다
    spi_flash=tuple(range(24, 31)),
    strapping=(4, 5, 8, 9, 15),
    adc1=tuple(range(0, 7)),
    adc2=(),  # 칩에 ADC2 가 존재하지 않는다
    # C6 는 U0TXD(GPIO16)만 출처가 확실하다. 부팅 글리치 핀 목록은 공식 문서에서
    # 못 찾았다 — **없어서 비운 게 아니라 못 찾아서 비웠다.** 지어내지 않는다.
    boot_output=(16,),
    boot_log_tx=16,
)

ESP32S3 = Chip(
    id="esp32s3",
    name="ESP32-S3",
    input_only=(),  # S3 는 입력 전용 핀이 없다 — 모든 GPIO 가 양방향
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
)

CHIPS: dict[str, Chip] = {c.id: c for c in (ESP32, ESP32C6, ESP32S3)}


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
