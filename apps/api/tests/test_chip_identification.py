"""칩을 어떻게 알아보는가 — 표에 넣는 것보다 알아보는 것이 어렵다.

남의 보드 28개를 재보니 **부품번호가 나온 보드가 5개뿐**이었다. 나머지는 `MPN` 칸을
안 채웠을 뿐, 회로도에는 `luat-esp32-c3_socket` · `Pico` 라고 그대로 적혀 있었다.
그걸 안 봐서 칩을 모른다고 했고, 칩이 필요한 규칙 5개가 통째로 죽어 있었다.
"""

from __future__ import annotations

from prefab.chips import BOARD_TO_CHIP, CHIPS
from prefab.netlist.detect import parse_any
from prefab.netlist.graph import Graph
from prefab.rules.r01_unusable_pin import chip_of
from prefab.types import Context


def _ctx(value: str) -> Context:
    text = f"""<?xml version="1.0" encoding="UTF-8"?>
<export version="E">
  <components><comp ref="U1"><value>{value}</value></comp></components>
  <nets><net code="1" name="/GND"><node ref="U1" pin="1" pinfunction="GND"/></net></nets>
</export>
"""
    return Context(netlist=Graph(parse_any(text, filename="b.net.xml")),
                   firmware=None, bom=None, datasheet=None)


def test_부품번호_칸이_비어도_부품_값으로_칩을_알아본다():
    """실측 보드에 적혀 있던 문자열 그대로다."""
    assert chip_of(_ctx("luat-esp32-c3_socket")).id == "esp32c3"
    assert chip_of(_ctx("ESP32-H2 SuperMini (2.54mm 1x9)")).id == "esp32h2"


def test_보드_이름은_정확히_같을_때만_인정한다():
    """**`Pico 2` 는 RP2040 이 아니라 RP2350 이다.**

    부분일치로 `pico` 를 잡으면 `Pico 2` 가 RP2040 으로 새고, 그러면 **다른 칩의
    핀 제약으로 판정**하게 된다. 못 잡는 것보다 나쁘다.
    실측 보드 `picoX7` 의 값이 정확히 `Pico 2 (RP2350)` 였다.
    """
    assert chip_of(_ctx("Pico")).id == "rp2040"
    assert chip_of(_ctx("RaspberryPi_Pico")).id == "rp2040"
    assert chip_of(_ctx("Pico 2 (RP2350)")) is None      # 우리 표에 없는 칩
    assert chip_of(_ctx("Pico-Audio")) is None           # 보드가 아니라 확장 모듈


def test_아무_값이나_칩으로_읽지_않는다():
    """값 칸에는 `10k 0.1%` 같은 것이 훨씬 많다. 아는 것만 알아본다."""
    for junk in ("10k 0.1%", "CAP100nF", "Conn_01x04_Male", "SW_Push", "74HC595"):
        assert chip_of(_ctx(junk)) is None


def test_별칭이_가리키는_칩은_표에_있어야_한다():
    """별칭만 늘리고 칩을 안 넣으면 조용히 None 이 된다."""
    for board, chip_id in BOARD_TO_CHIP.items():
        assert chip_id in CHIPS, f"{board} → {chip_id} 가 칩 표에 없다"


def test_RP2040_의_빈칸은_못_찾은_게_아니라_없는_것이다():
    """ESP32 는 플래시·USB·스트래핑이 GPIO 를 빌려 쓰지만 RP2040 은 따로 뽑아 놨다.

    이 빈칸을 "출처를 못 찾았다"로 읽으면 안 된다. 규칙이 조용한 것이 정답이다.
    """
    rp = CHIPS["rp2040"]
    assert rp.spi_flash == ()      # QSPI 는 별도 뱅크라 GPIO 번호와 안 겹친다
    assert rp.strapping == ()      # 부팅 모드는 BOOTSEL 버튼이고 GPIO 가 아니다
    assert rp.usb == ()            # USB_DP · USB_DM 은 전용 핀이다
    assert rp.adc1 == (26, 27, 28, 29)
    assert rp.logic_volts == 3.3


def test_모든_칩이_로직_전압을_안다():
    """도메인 추론이 여기 기댄다. 하나라도 비면 그 보드만 배선으로 추측하게 된다."""
    for chip in CHIPS.values():
        assert chip.logic_volts is not None, f"{chip.name} 의 logic_volts 가 비었다"


def test_쿼드_전용_플래시_핀은_플래시로_치지_않는다():
    """**칩을 추가하자마자 오탐 3건이 났다.** 그 자리를 고정한다.

    ESP-IDF 가 "GPIO12 ~ GPIO17 are **usually** used for SPI flash" 라고 쓰는데,
    그 "usually" 가 GPIO12(SPIHD)·GPIO13(SPIWP)다 — **쿼드(QIO) 모드에서만** 쓴다.
    2선(DIO)으로 플래시를 다는 보드에서는 남는 GPIO 이고, LuatOS CORE-ESP32-C3 가
    정확히 그래서 그 둘을 LED 로 뽑아 쓴다. 우리는 "부팅이 실패한다" 고 치명을 냈다.

    넷리스트는 플래시 모드를 말해 주지 않는다. 모르면 말하지 않는다 (헌법 2-2).
    """
    c3 = CHIPS["esp32c3"]
    assert 12 not in c3.spi_flash and 13 not in c3.spi_flash
    # 모드와 무관하게 항상 플래시인 것들은 남긴다
    assert set(c3.spi_flash) == {14, 15, 16, 17}
