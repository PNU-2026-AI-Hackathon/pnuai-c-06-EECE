"""홀드아웃 보드에서 나온 오탐을 고정한다.

**한 번도 안 넣어 본 남의 보드 10개**에 처음 돌려서 나온 것들이다. 우리가 튜닝에
쓴 6개와 겹치지 않는다 — 그 6개에서 오탐 0건을 만든 뒤였는데도 14건이 나왔다.
같은 데이터로 재면 그 숫자를 못 본다는 것이 이 파일의 존재 이유다.
"""

from __future__ import annotations

from prefab.netlist.detect import parse_any
from prefab.netlist.graph import CONFIDENCE_HIGH, Graph

# `3V3` 핀과 `5V` 핀을 둘 다 뽑는 5V 보드 (Mega Pro Embed / ATmega2560).
# 앞에 걸린 `3V3` 를 골라 3.3V 보드로 읽었고, 붙어 있던 5V 부품이 전부 오탐이 됐다.
BOARD_WITH_TWO_RAILS = """<?xml version="1.0" encoding="UTF-8"?>
<export version="E">
  <components>
    <comp ref="J1"><value>Mega_Pro_Embed</value></comp>
    <comp ref="U5"><value>SENSOR5V</value></comp>
  </components>
  <nets>
    <net code="1" name="/5V"><node ref="J1" pin="1" pinfunction="5V"/></net>
    <net code="2" name="/3V3"><node ref="J1" pin="2" pinfunction="3V3"/></net>
    <net code="3" name="/GND"><node ref="J1" pin="3" pinfunction="GND"/>
      <node ref="U5" pin="3" pinfunction="GND"/></net>
    <net code="4" name="/5V"><node ref="U5" pin="1" pinfunction="VCC"/></net>
    <net code="5" name="/SIG"><node ref="J1" pin="4" pinfunction="D2"/>
      <node ref="U5" pin="2" pinfunction="OUT"/></net>
  </nets>
</export>
"""

# 레벨 시프터 (SN74LV1T34, VCC=5V) 의 `IN` 핀이 3.3V MCU 와 같은 네트에 있다.
LEVEL_SHIFTER = """<?xml version="1.0" encoding="UTF-8"?>
<export version="E">
  <components>
    <comp ref="U1"><value>STM32F446RE</value></comp>
    <comp ref="U2"><value>SN74LV1T34DBVR</value></comp>
  </components>
  <nets>
    <net code="1" name="/3.3V"><node ref="U1" pin="1" pinfunction="VDD"/></net>
    <net code="2" name="/5V"><node ref="U2" pin="5" pinfunction="VCC"/></net>
    <net code="3" name="/GND"><node ref="U1" pin="2" pinfunction="VSS"/>
      <node ref="U2" pin="3" pinfunction="GND"/></net>
    <net code="4" name="/LED.DI"><node ref="U1" pin="14" pinfunction="PA8"/>
      <node ref="U2" pin="2" pinfunction="IN"/></net>
  </nets>
</export>
"""


def test_전원핀이_둘이면_로직_전압을_단정하지_않는다():
    """`3V3` 를 먼저 만났다고 3.3V 보드라고 하면 안 된다.

    5V 로직 보드(ATmega2560)가 레귤레이터 출력으로 `3V3` 핀을 같이 뽑는다.
    앞에 걸린 것을 고르는 바람에 붙어 있던 5V 부품이 전부 "상위가 하위를 직결"
    로 떴다 — **한 보드에서 7건**. 모르면 모른다고 한다 (헌법 2-2).
    """
    g = Graph(parse_any(BOARD_WITH_TWO_RAILS, filename="b.net.xml"))
    d = g.domain("J1")
    assert d.volts is None
    assert d.confidence != CONFIDENCE_HIGH
    assert "3V3" in d.basis and "5V" in d.basis   # 무엇 때문에 모르는지 말한다


def test_레벨_시프터의_입력핀은_상위_구동부가_아니다():
    """**해결책을 결함으로 지목하고 있었다.**

    `SN74LV1T34` 는 3.3V 를 5V 로 올려 주는 부품이다. 그 `IN` 핀이 3.3V MCU 와
    만나는 것이 정상 사용법인데, VCC 가 5V 라는 이유로 R12 가 치명을 냈다.
    문구는 "사이에 레벨 시프터도 없습니다" 였다 — 레벨 시프터를 가리키면서.
    """
    g = Graph(parse_any(LEVEL_SHIFTER, filename="b.net.xml"))
    assert g.receives("U2", "/LED.DI")      # 핀 이름이 스스로 밝힌다
    assert not g.drives("U2", "/LED.DI")


def test_입력이라고_말하지_않은_핀은_입력으로_치지_않는다():
    """모르는 것을 "입력이다" 로 쓰면 경고가 조용히 사라진다.

    `INT`(인터럽트)·`INH`(억제)까지 입력으로 먹으면 R12 가 통째로 침묵한다.
    오탐을 줄이려다 미탐을 만드는 것이 이 수정에서 제일 위험한 실패다.
    """
    g = Graph(parse_any(LEVEL_SHIFTER, filename="b.net.xml"))
    assert not g.receives("U1", "/LED.DI")   # `PA8` 은 방향을 말해 주지 않는다


CONTROL_NET = """<?xml version="1.0" encoding="UTF-8"?>
<export version="E">
  <components>
    <comp ref="A3"><value>ESP32</value></comp>
    <comp ref="Q1"><value>MOSFET</value></comp>
  </components>
  <nets>
    <net code="1" name="/3V3"><node ref="A3" pin="1" pinfunction="VCC"/></net>
    <net code="2" name="/GND"><node ref="A3" pin="2" pinfunction="GND"/>
      <node ref="Q1" pin="2" pinfunction="S"/></net>
    <net code="3" name="24V_ON"><node ref="A3" pin="7" pinfunction="IO7"/>
      <node ref="Q1" pin="1" pinfunction="G"/></net>
  </nets>
</export>
"""


def test_제어_신호_이름은_전압_주장이_아니다():
    """`24V_ON` 은 24V 네트가 아니라 **24V 를 켜는 신호**다.

    3.3V MCU 가 내는 것이 정상인데 R11 이 "이름은 24V 라는데 구동부는 3.3V" 라고
    경고했다. 이름이 제어 대상을 말할 때 그 네트의 전압은 모르는 것이다 (헌법 2-2).
    """
    from prefab.netlist.graph import names_a_control

    assert names_a_control("24V_ON")
    assert names_a_control("/5V_EN")
    assert not names_a_control("/12V_BUS")   # 진짜 레일까지 먹으면 R11 이 죽는다

    g = Graph(parse_any(CONTROL_NET, filename="b.net.xml"))
    from prefab.rules import r11_net_name_domain as r11
    from prefab.types import Context

    ctx = Context(netlist=g, firmware=None, bom=None, datasheet=None)
    assert [f for f in r11.check(ctx) if f.net == "24V_ON"] == []


# ---------------------------------------------------------------- 두 번째 홀드아웃
#
# 새 보드 28개. 위 셋을 고친 뒤에 처음 돌린 표본이라 **또 겹치지 않는다.**

def test_못_읽은_핀_표현이_있으면_R08은_단정하지_않는다():
    """R08 의 주장은 "다 읽어봤는데 없더라" 다.

    키보드 펌웨어가 `int key_pins[] = {D4, D1, ...}` 로 20개를 적고
    `pinMode(key_pins[i], INPUT_PULLUP)` 로 돌린다. 파서는 `key_pins[i]` 를 못 읽고
    **그 사실을 이미 기록해 두는데**, 규칙이 그걸 안 봐서 확신에 찬 경고가 18건 났다.
    """
    from prefab.firmware.arduino import analyze as fw_analyze

    src = {
        "main.cpp": (
            "int key_pins[] = {4, 5, 6};\n"
            "void setup() {\n"
            "  for (int i = 0; i < 3; i++) pinMode(key_pins[i], INPUT_PULLUP);\n"
            "  pinMode(2, OUTPUT);\n"
            "}\n"
        )
    }
    fw = fw_analyze(src)
    assert fw.unresolved, "배열 인덱스를 못 읽었다는 것을 파서가 알아야 한다"
    assert "배열" in fw.unresolved_summary


def test_버스_라이브러리는_코드와_라이브러리_둘_다_봐야_한다():
    """네트 이름 하나로 경고를 지우지 않는다.

    `SPI.h` 를 들여왔고 네트 이름이 `MISO` 일 때만 "우리가 못 보는 자리" 라고 말한다.
    네트 이름만 맞으면 아무 말도 안 한다 — 이름은 아무렇게나 붙일 수 있다 (헌법 11절).
    """
    from prefab.rules.r08_connected_but_unused import _bus_blind

    class FW:
        includes = ("spi", "arduino")

    class NoSPI:
        includes = ("arduino",)

    assert _bus_blind(FW(), "/MISO") is not None
    assert _bus_blind(FW(), "/SCK") is not None
    assert _bus_blind(NoSPI(), "/MISO") is None    # 라이브러리를 안 쓰면 모른다
    assert _bus_blind(FW(), "/RELAY_IN") is None   # 버스 신호가 아니다


HEADER_40PIN = """<?xml version="1.0" encoding="UTF-8"?>
<export version="E">
  <components><comp ref="J14"><value>RPi_Header</value></comp></components>
  <nets>
    <net code="1" name="/+5V"><node ref="J14" pin="2" pinfunction="Pin_2"/></net>
    <net code="2" name="/GND"><node ref="J14" pin="6" pinfunction="Pin_6"/></net>
""" + "".join(
    f'    <net code="{i}" name="/SIG{i}"><node ref="J14" pin="{i}" pinfunction="Pin_{i}"/></net>\n'
    for i in range(10, 40)
) + """  </nets>
</export>
"""


def test_커넥터는_레일에_닿았다고_그_전압_부품이_아니다():
    """40핀 헤더가 +5V·GND 에 닿는다고 5V 부품이 되면 안 된다.

    그렇게 판정해서 거기 물린 3.3V 마이크가 전부 오탐이 됐다 — 한 보드에서 10건.
    나머지 36핀은 전부 3.3V 신호다. R11 은 이 전제를 이미 막고 있었다.
    """
    g = Graph(parse_any(HEADER_40PIN, filename="b.net.xml"))
    assert g.domain("J14").volts is None
