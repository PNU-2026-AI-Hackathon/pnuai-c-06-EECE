"""R17 — 한 핀이 서로 다른 두 네트에 있음.

**LLM 이 찾았고 코드가 확인한 규칙이다.** 홀드아웃 보드 `EEPROM_programmer` 에서
Sonnet 이 "U3 15번 핀이 두 넷에 있다" 고 했고, 넷리스트를 열어 보니 사실이었다.
아래 픽스처는 그 보드의 해당 부분만 최소로 옮긴 것이다.
"""

from __future__ import annotations

from prefab.netlist.detect import parse_any
from prefab.netlist.graph import Graph
from prefab.rules import r17_pin_on_two_nets as r17
from prefab.types import Context, Verdict


def _ctx(text: str, filename: str = "b.net.xml") -> Context:
    return Context(netlist=Graph(parse_any(text, filename=filename)),
                   firmware=None, bom=None, datasheet=None)


# 실측: EEPROM 의 데이터 선 두 개가 U3 15번 핀에 함께 물렸다.
SHORTED = """<?xml version="1.0" encoding="UTF-8"?>
<export version="E">
  <components>
    <comp ref="A1"><value>Arduino_Nano</value></comp>
    <comp ref="U3"><value>AT28C256</value></comp>
  </components>
  <nets>
    <net code="1" name="/GND"><node ref="A1" pin="4" pinfunction="GND"/>
      <node ref="U3" pin="14" pinfunction="GND"/></net>
    <net code="2" name="/D5"><node ref="A1" pin="13" pinfunction="D10"/>
      <node ref="U3" pin="15" pinfunction="I/O5"/></net>
    <net code="3" name="/D7"><node ref="A1" pin="15" pinfunction="D12"/>
      <node ref="U3" pin="15" pinfunction="I/O7"/></net>
  </nets>
</export>
"""

# 같은 보드에서 핀 번호만 바로잡은 것. 나머지는 글자 하나 안 바꿨다.
CLEAN = SHORTED.replace('<node ref="U3" pin="15" pinfunction="I/O7"/>',
                        '<node ref="U3" pin="17" pinfunction="I/O7"/>')


def test_양성_한_핀이_두_네트에_있으면_치명():
    found = r17.check(_ctx(SHORTED))
    assert len(found) == 1
    f = found[0]
    assert f.rule == "R17" and f.verdict == Verdict.FAIL
    assert "/D5" in f.claim and "/D7" in f.claim
    # 심볼이 붙여둔 이름이 다르다는 것 자체가 근거다
    assert "I/O5" in f.claim and "I/O7" in f.claim
    # 네트가 둘이라 하나를 고르지 않는다
    assert f.net is None


def test_음성_핀_번호가_다르면_아무_말도_안_한다():
    assert r17.check(_ctx(CLEAN)) == []


def test_미해결_이름이_잘리는_형식에서는_판정하지_않는다():
    """IPC-D-356 은 핀 이름을 4자로 자른다.

    `(부품, 핀)` 만으로 보면 **우리 실측 보드에서 3건이 헛난다** — `U1` 의 D0·D1·D2 가
    전부 `LP-G` 이고 K1 의 패드 6개가 전부 `pad-` 다. 이름이 같다고 같은 핀이 아니다.
    좌표까지 넣어 물리 패드로 갈라야 0건이 된다.
    """
    text = open("tests/fixtures/esp32-c6-presence-smart-light.d356").read()
    assert r17.check(_ctx(text, filename="b.d356")) == []


# 심볼이 핀 번호를 안 붙이면 KiCad 는 `pin=""` 으로 내보낸다.
# **이 규칙이 처음 실전에서 잡은 2건 중 1건이 이 오탐이었다** (`picoX7` 의 U2).
NO_PIN_NUMBERS = """<?xml version="1.0" encoding="UTF-8"?>
<export version="E">
  <components><comp ref="U2"><value>PCM5102</value></comp>
    <comp ref="J3"><value>AudioJack</value></comp></components>
  <nets>
    <net code="1" name="Net-(J3-PadG)"><node ref="J3" pin="G"/>
      <node ref="U2" pin="" pinfunction="GND_"/></net>
    <net code="2" name="Net-(U2-LINE_OUT_L)"><node ref="J3" pin="S"/>
      <node ref="U2" pin="" pinfunction="LINE_OUT_L_"/></net>
    <net code="3" name="Net-(U2-LINE_OUT_R)"><node ref="J3" pin="T"/>
      <node ref="U2" pin="" pinfunction="LINE_OUT_R_"/></net>
  </nets>
</export>
"""


def test_핀_번호가_없으면_같은_핀인지_알_수_없다():
    """번호가 비면 서로 다른 핀 셋이 한 신원으로 뭉친다.

    `GND` · `LINE_OUT_L` · `LINE_OUT_R` 은 명백히 다른 핀인데 셋 다 `pin=""` 이라
    "한 핀이 3개 네트에" 라는 오탐이 났다. 이름으로 대신 가르지 않는다 —
    이름이 잘리는 형식에서 정확히 그 방식이 실측 보드에서 3건을 헛나게 했다.
    """
    assert r17.check(_ctx(NO_PIN_NUMBERS)) == []
