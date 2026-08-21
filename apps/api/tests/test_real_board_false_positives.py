"""남의 실제 보드에서 나온 오탐 5건 — 각각이 어떤 버그였는지.

**합성 케이스에서 오탐 0% 였는데 남의 보드 6개에서 45건이 났다.** 45 → 5 까지 줄인 뒤
남은 5건을 하나씩 파보니 **셋 다 규칙이 아니라 그 아래층 버그**였다. 여기서 고정한다.

여기 있는 것은 전부 *우리가 만든 케이스가 아니라* 실제 보드에서 온 모양이다.
합성 케이스만 보면 이런 것들이 있는 줄도 모른다 (`_docs/규모_실험.md`).
"""

from __future__ import annotations

import pytest

from prefab.netlist.detect import parse_any
from prefab.netlist.graph import Graph, volts
from prefab.netlist.kicadxml import clean_pin_name
from prefab.rules import r11_net_name_domain as r11
from prefab.types import Context

# ── 1. 전압 토큰이 소수점 표기를 못 읽었다 ──────────────────────────


@pytest.mark.parametrize(
    "name,expected",
    [
        ("+3.3V", 3.3),   # KiCad 가 흔히 쓰는 표기 — 3.0 으로 읽고 있었다
        ("3.3V", 3.3),
        ("3V3", 3.3),     # 유럽식은 원래 됐다
        ("1V8", 1.8),
        ("5V_BUS", 5.0),
        ("+12V", 12.0),
        ("12.5V", 12.5),
        ("PRESENCE_3V3", 3.3),
    ],
)
def test_전압_토큰이_소수점_표기를_읽는다(name, expected):
    assert volts(name) == expected


def test_0점9V_를_9V_로_읽지_않는다():
    """**제일 위험했던 것.** 앞의 `0.` 을 건너뛰고 `9V` 를 잡아 9.0V 로 읽었다.

    0.9V 코어 레일을 9V 로 보면 R11·R12 가 열 배 틀린 근거로 경고를 낸다.
    """
    assert volts("0.9V") == 0.9


@pytest.mark.parametrize("name", ["GND", "SIG_A", "USB_D+", "VBUS", ""])
def test_전압이_없는_이름에서는_아무것도_안_읽는다(name):
    assert volts(name) is None


# ── 2. 전원 레일 판정이 핀 이름 대신 번호를 봤다 ────────────────────


SCHEMATIC = """<?xml version="1.0"?>
<export version="E">
  <components>
    <comp ref="U1"><value>MCU</value></comp>
    <comp ref="U2"><value>SENSOR</value></comp>
  </components>
  <nets>
    <net name="+5V">
      <node ref="U1" pin="15" pinfunction="VIN"/>
      <node ref="U2" pin="1" pinfunction="VCC"/>
    </net>
    <net name="GND">
      <node ref="U1" pin="16" pinfunction="GND"/>
      <node ref="U2" pin="2" pinfunction="GND"/>
    </net>
  </nets>
</export>
"""


def test_전원_레일을_핀_이름으로_알아본다():
    """`p.pin` 은 회로도 넷리스트에서 **번호**(`15`)다.

    거기에 `VCC|VDD|VIN…` 패턴을 대면 하나도 안 걸려서 전원 레일이 통째로
    **신호**로 분류되고, R11·R12 가 전원 레일 위에서 돈다.
    `pins_of()` 에서 이미 한 번 고친 것과 같은 버그가 여기 남아 있었다.
    """
    g = Graph(parse_any(SCHEMATIC))
    assert g.is_power_rail("+5V")
    assert "+5V" not in g.signal_nets()


# ── 3. 좌표가 없는 형식에서 좌표 클러스터링이 돌았다 ────────────────


def test_좌표가_없으면_클러스터링을_안_한다():
    """없는 좌표를 `0.0` 으로 채우면 부품의 패드가 전부 한 점에 뭉친다.

    그러면 "이 부품의 모든 핀이 같은 물리 그룹" 이라는 답이 나오는데, 그건 복원이
    아니라 지어낸 것이다. 그 답을 받은 도메인 추론이 IC 를 "레일+GND 동거" 로 보고
    5V 부품이라 판정했고 R12 오탐 2건이 됐다.
    """
    nl = parse_any(SCHEMATIC)
    assert nl.HAS_COORDINATES is False
    g = Graph(nl)
    assert g.clusters("U1") == {}


def test_IPC_는_좌표가_있다고_말한다():
    """d356 은 좌표가 본문이다. 여기까지 꺼버리면 K1 패드 그룹 복원이 죽는다."""
    from prefab.netlist.d356 import Netlist

    assert Netlist.HAS_COORDINATES is True


# ── 4. KiCad 의 렌더링 표기를 안 벗겼다 ─────────────────────────────


@pytest.mark.parametrize(
    "raw,clean",
    [
        ("V_{CC}", "VCC"),      # 아래첨자는 이름의 일부다
        ("A_{0}", "A0"),
        ("~{CHRG}", "~CHRG"),   # 오버바는 뜻이 있다. 버리지 않는다
        ("~{ON}/OFF", "~ON/OFF"),
        ("GPIO3", "GPIO3"),     # 장식이 없으면 그대로
    ],
)
def test_KiCad_핀_이름_장식을_벗긴다(raw, clean):
    assert clean_pin_name(raw) == clean


def test_V_CC_를_공급핀으로_알아본다():
    """`V_{CC}` 가 공급핀 패턴에 안 걸려서 충전 IC 하나가 도메인을 못 읽었다.

    그래서 "레일 소속" 추측으로 떨어졌고, 그 추측이 R12 오탐 2건이 됐다.
    """
    text = SCHEMATIC.replace('pinfunction="VCC"', 'pinfunction="V_{CC}"')
    g = Graph(parse_any(text))
    d = g.domain("U2")
    assert d.volts == 5.0
    assert d.confidence == "high", d.basis


# ── 5. R11 이 "전원을 받는 것" 을 "구동하는 것" 이라고 했다 ──────────


POWERED_BY_NET = """<?xml version="1.0"?>
<export version="E">
  <components><comp ref="U1"><value>MCU</value></comp></components>
  <nets>
    <net name="/5V_IN">
      <node ref="U1" pin="15" pinfunction="VIN"/>
      <node ref="SW1" pin="1" pinfunction="A"/>
    </net>
    <net name="/3V3">
      <node ref="U1" pin="2" pinfunction="3V3"/>
      <node ref="C1" pin="1"/>
    </net>
    <net name="GND">
      <node ref="U1" pin="16" pinfunction="GND"/>
      <node ref="C1" pin="2"/>
    </net>
  </nets>
</export>
"""


def test_전원을_받는_핀은_소스가_아니다():
    """`U1.VIN → /5V_IN` 을 보고 "이 네트를 구동하는 U1 은 3.3V" 라고 말했다.

    거꾸로다 — U1 이 5V 를 먹고 안에서 3.3V 를 만든다. 부품의 내부 도메인은
    **자기 전원 입력 네트의 전압에 대해 아무 말도 하지 않는다.**
    """
    g = Graph(parse_any(POWERED_BY_NET))
    assert g.domain("U1").volts == 3.3          # 도메인 자체는 맞게 읽는다
    assert r11.check(Context(netlist=g)) == []  # 그걸로 5V 네트를 반박하지 않는다


# ── 6. R11 이 "어느 레일에 닿아 있더라" 로 이름을 반박했다 ───────────


CONNECTOR = """<?xml version="1.0"?>
<export version="E">
  <components><comp ref="J3"><value>Conn_01x04</value></comp></components>
  <nets>
    <net name="+5V"><node ref="J3" pin="2" pinfunction="Pin_2"/><node ref="U9" pin="1" pinfunction="VCC"/></net>
    <net name="24V_ON"><node ref="J3" pin="4" pinfunction="Pin_4"/><node ref="R1" pin="1"/></net>
    <net name="GND"><node ref="J3" pin="3" pinfunction="Pin_3"/><node ref="R1" pin="2"/></net>
  </nets>
</export>
"""


def test_커넥터가_레일에_닿았다고_핀마다_그_전압인_것은_아니다():
    """4핀 커넥터가 2번 핀에서 +5V 에 닿는다는 이유로 도메인이 5V 가 됐고,
    그걸 근거로 `24V_ON` 이라는 이름을 "사실은 5V" 라고 반박했다.

    커넥터는 핀마다 다른 신호를 나른다 — **부품 하나에 도메인 하나**가 안 선다.
    """
    g = Graph(parse_any(CONNECTOR))
    assert r11.check(Context(netlist=g)) == []
