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
