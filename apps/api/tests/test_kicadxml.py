"""회로도 넷리스트(kicadxml) 파서.

**이 파서가 존재하는 이유는 하나다 — 핀에 이름이 붙어서 온다.**

IPC-D-356 은 제조용이라 핀 이름을 안 싣는다. 그래서 KiCad 로 만든 실제 보드
3개에서 `pinmap` 이 하나도 안 풀렸고 R07·R08 이 통째로 침묵했다
(`_docs/규모_실험.md` B — 통제 실험으로 원인을 확정했다).

여기 있는 테스트는 그 침묵이 다시 돌아오지 않게 막는다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from prefab.netlist.d356 import NetlistParseError
from prefab.netlist.graph import Graph
from prefab.netlist.kicadxml import parse_text, strip_pin_number

FIXTURE = Path(__file__).parent / "fixtures" / "schematic-gpio-named.net.xml"


@pytest.fixture()
def netlist():
    return parse_text(FIXTURE.read_text(encoding="utf-8"), filename=FIXTURE.name)


# ── 핀 이름 ─────────────────────────────────────────────────────────


def test_핀_이름이_잘리지_않고_온다(netlist):
    """IPC-D-356 이면 4자에서 잘렸을 이름들이다."""
    names = {
        (p.ref, p.pin): p.name
        for pads in netlist.nets.values()
        for p in pads
        if p.name
    }
    assert names[("U1", "16")] == "GPIO10"
    assert names[("U1", "28")] == "U0TXD"


def test_심볼이_붙여둔_핀번호_접미를_뗀다(netlist):
    """KiCad 심볼 라이브러리는 `GPIO3_8` 처럼 핀 번호를 이름 끝에 붙여 둔다."""
    pad = next(p for pads in netlist.nets.values() for p in pads if p.pin == "8")
    assert pad.name == "GPIO3"


def test_접미가_핀번호와_다르면_이름을_안_건드린다():
    """규약이 다른 도구에서 이름 끝을 잘라먹지 않는다."""
    assert strip_pin_number("GPIO3_8", "8") == "GPIO3"
    assert strip_pin_number("GPIO3_8", "9") == "GPIO3_8"
    assert strip_pin_number("VDD3P3", "2") == "VDD3P3"
    # 이름이 통째로 접미만인 경우 — 빈 이름을 만들지 않는다
    assert strip_pin_number("_8", "8") == "_8"


def test_이름이_없는_핀은_None_이다(netlist):
    """수동 소자는 pinfunction 이 없다. **없는 것을 지어내지 않는다.**"""
    pad = next(
        p for pads in netlist.nets.values() for p in pads if p.ref == "R1" and p.pin == "2"
    )
    assert pad.name is None


# ── 이 파서가 풀어주는 것 ────────────────────────────────────────────


def test_핀_이름으로_GPIO_패드가_풀린다(netlist):
    """B 실험에서 KiCad 보드는 이 값이 0이었다. 그게 R07·R08 침묵의 원인이었다."""
    gpio = {p.gpio for p in Graph(netlist).pinmap.gpio_pads()}
    assert gpio == {3, 8, 9, 10}


def test_커넥터의_Pin_1_을_GPIO_로_오인하지_않는다(netlist):
    """`Pin_1` 은 GPIO 가 아니다. 오인하면 그 위의 판정이 전부 거짓이 된다."""
    assert all(i.ref != "J1" for i in Graph(netlist).pinmap.all())


def test_부품번호와_데이터시트가_함께_온다(netlist):
    """IPC-D-356 에는 이 정보가 통째로 없다. BOM 없이도 부품을 짚을 수 있다."""
    u1 = netlist.components["U1"]
    assert u1.value == "ESP32-C3-MINI-1"
    assert u1.mpn == "C2913196"
    assert u1.datasheet.endswith(".pdf")
    # MPN 필드 이름은 라이브러리마다 다르다
    assert netlist.components["R1"].mpn == "RC0402FR-0710KL"


def test_부품번호가_없으면_None_이다(netlist):
    assert netlist.components["J1"].mpn is None


# ── 연결 판정 ───────────────────────────────────────────────────────


def test_상대가_없는_핀은_미연결이다(netlist):
    """이름이 `unconnected-` 든 아니든 패드 수로 본다 (도구 무관)."""
    assert netlist.is_dangling("unconnected-(U1-GPIO8-Pad14)")
    assert netlist.is_dangling("BUTTON")  # 이름은 멀쩡한데 혼자다
    assert not netlist.is_dangling("ADC_IN")


def test_좌표가_없어도_핀_하나가_정해진다(netlist):
    """회로도에는 좌표가 없다. 핀 번호가 부품 안에서 유일하므로 그래도 정해진다."""
    assert netlist.net_at("U1", "16", None, None) == "SENSOR_PWR_EN"
    assert netlist.net_of("U1", "8") == "ADC_IN"


# ── 못 하는 것을 말하는가 ───────────────────────────────────────────


def test_좌표가_없다는_사실을_숨기지_않는다(netlist):
    """기하 기반 경로가 안 도는 것은 형식의 성질이다. 조용히 넘기지 않는다 (헌법 2-2)."""
    notes = " ".join(netlist.parse_notes())
    assert "좌표 없음" in notes


def test_회로도가_실어준_부품_수를_알린다(netlist):
    assert "부품 3개" in " ".join(netlist.parse_notes())


# ── 아닌 파일 ───────────────────────────────────────────────────────


def test_XML_이_아니면_거절한다():
    with pytest.raises(NetlistParseError):
        parse_text("317GND   VIA  MD0118PA00X+016732Y-004724")


def test_다른_XML_이면_무엇이_필요한지_알려준다():
    with pytest.raises(NetlistParseError, match="kicad-cli"):
        parse_text("<?xml version='1.0'?><svg><g/></svg>")


def test_네트가_없으면_거절한다():
    with pytest.raises(NetlistParseError, match="네트"):
        parse_text("<?xml version='1.0'?><export version='E'><nets/></export>")
