"""R15 — 양성 / 음성 / 미해결.

**우리 보드에서 실제로 난 결함이 만든 규칙이다.** 3.3V MCU 가 5V 릴레이 모듈의
액티브 로우 입력을 몰았고, 끄려고 낸 3.3V 가 하이로 안 읽혀 **릴레이가 안 꺼졌다.**
합성 케이스로는 이 모양이 있는 줄도 몰랐다 — R14 가 남의 보드에서 나온 것과 같은 경로다.
"""

from __future__ import annotations

from pathlib import Path

from prefab.datasheet.facts import (
    CONF_HIGH,
    OPEN_DRAIN,
    OUTPUT_TYPE,
    VIH_MIN,
    Fact,
    FactSet,
)
from prefab.firmware import analyze as analyze_firmware
from prefab.netlist.detect import parse_any
from prefab.netlist.graph import Graph
from prefab.rules import r15_output_below_vih as r15
from prefab.types import Context, Verdict

FIXTURES = Path(__file__).parent / "fixtures"


# ── 회로: 3.3V MCU 가 5V 모듈 입력을 몬다 ───────────────────────────

NETLIST = """<?xml version="1.0"?>
<export version="E">
  <components>
    <comp ref="U1"><value>XIAO-ESP32C6</value>
      <fields><field name="MPN">XIAO-ESP32C6</field></fields></comp>
    <comp ref="K1"><value>relay</value>
      <fields><field name="MPN">RELAY-MOD</field></fields></comp>
  </components>
  <nets>
    <net name="3V3">
      <node ref="U1" pin="2" pinfunction="3V3"/>
    </net>
    <net name="5V_BUS">
      <node ref="K1" pin="1" pinfunction="VCC"/>
      <node ref="U1" pin="1" pinfunction="5V"/>
    </net>
    <net name="RELAY_IN">
      <node ref="U1" pin="9" pinfunction="D5"/>
      <node ref="K1" pin="3" pinfunction="IN"/>
    </net>
    <net name="GND">
      <node ref="U1" pin="3" pinfunction="GND"/>
      <node ref="K1" pin="2" pinfunction="GND"/>
    </net>
  </nets>
</export>
"""

FIRMWARE = {
    "main.ino": (
        "#define RELAY_PIN D5\n"
        "void setup(){ pinMode(RELAY_PIN, OUTPUT); }\n"
        "void loop(){ digitalWrite(RELAY_PIN, HIGH); }\n"
    )
}


def _ctx(*, facts: "FactSet | None" = None, firmware=None) -> Context:
    return Context(
        netlist=Graph(parse_any(NETLIST)),
        firmware=analyze_firmware(firmware if firmware is not None else FIRMWARE),
        datasheet=facts,
    )


def _fact(field: str, value) -> FactSet:
    return FactSet(
        [
            Fact(
                mpn="RELAY-MOD",
                field=field,
                value=value,
                unit="V" if field == VIH_MIN else None,
                table="Electrical Characteristics",
                page=3,
                quote="Input high voltage 4.5 V min",
                confidence=CONF_HIGH,
            )
        ]
    )


# ── 양성 ────────────────────────────────────────────────────────────


def test_문턱을_알면_못_민다고_판정한다():
    """`vih_min` 4.5V 인데 MCU 는 3.3V 까지밖에 못 낸다."""
    findings = r15.check(_ctx(facts=_fact(VIH_MIN, 4.5)))
    assert len(findings) == 1, findings
    f = findings[0]
    assert f.verdict is Verdict.FAIL
    assert "4.5" in f.claim and "3.3" in f.claim
    # 코드만 고쳐서는 안 된다는 것을 말해 준다 — 이게 이 규칙의 요점이다
    assert "코드만 고쳐서는" in f.suggestion


def test_근거가_회로도와_코드_양쪽에서_온다():
    findings = r15.check(_ctx(facts=_fact(VIH_MIN, 4.5)))
    kinds = {e.kind for e in findings[0].evidence}
    assert {"netlist", "firmware", "datasheet"} <= kinds, kinds


# ── 음성 ────────────────────────────────────────────────────────────


def test_문턱이_낮으면_해제한다():
    """5V 부품이라고 다 5V 문턱인 게 아니다 — TTL 호환 입력은 2.0V 면 하이다.

    **이게 이 규칙에서 제일 흔한 오탐이 될 자리다.**
    """
    findings = r15.check(_ctx(facts=_fact(VIH_MIN, 2.0)))
    assert len(findings) == 1
    assert findings[0].verdict is Verdict.PASS


def test_오픈드레인이면_MCU_가_하이를_정하지_않는다():
    findings = r15.check(_ctx(facts=_fact(OUTPUT_TYPE, OPEN_DRAIN)))
    assert len(findings) == 1
    assert findings[0].verdict is Verdict.PASS


def test_입력으로만_쓰는_핀은_대상이_아니다():
    """코드가 몰지 않으면 하이를 낼 일도 없다."""
    fw = {"main.ino": "#define RELAY_PIN D5\nvoid setup(){ pinMode(RELAY_PIN, INPUT); }\n"}
    assert r15.check(_ctx(firmware=fw)) == []


def test_상대가_스스로_출력이라고_밝히면_묻지_않는다():
    """`U2.OUT` 을 "5V 부품의 입력" 이라고 적고 있었다 — 넷리스트가 반대로 말하는데도.

    그 자리의 진짜 문제는 다른 것이다 (코드가 센서 출력에 자기 출력을 물렸다).
    R07·R08·R10 이 드리프트로 잡는다.
    """
    text = NETLIST.replace('pinfunction="IN"', 'pinfunction="OUT"')
    graph = Graph(parse_any(text))
    ctx = Context(netlist=graph, firmware=analyze_firmware(FIRMWARE))
    assert r15.check(ctx) == []


def test_전원을_받는_핀은_대상이_아니다():
    """`VCC` 가 걸린 네트에 입력 문턱을 묻는 것은 질문 자체가 틀렸다."""
    text = NETLIST.replace('pinfunction="IN"', 'pinfunction="VCC"')
    graph = Graph(parse_any(text))
    ctx = Context(netlist=graph, firmware=analyze_firmware(FIRMWARE))
    assert r15.check(ctx) == []


def test_같은_도메인이면_볼_것이_없다():
    text = NETLIST.replace('<net name="5V_BUS">', '<net name="3V3_BUS">')
    graph = Graph(parse_any(text))
    ctx = Context(netlist=graph, firmware=analyze_firmware(FIRMWARE))
    assert r15.check(ctx) == []


def test_실측_보드_기존_펌웨어에서는_조용하다():
    """그 펌웨어는 D5 를 안 쓴다. 뜨면 오탐이다."""
    from prefab.firmware import load_directory
    from prefab.runner import analyze

    a = analyze(
        (FIXTURES / "esp32-c6-presence-smart-light.d356").read_text(encoding="utf-8"),
        filename="b.d356",
        bom_bytes=(FIXTURES / "esp32-c6-presence-smart-light.bom.csv").read_bytes(),
        firmware_sources=load_directory(FIXTURES / "esp32-c6-presence-smart-light.firmware"),
    )
    assert [f for f in a.engine.findings if f.rule == "R15"] == []


# ── 미해결 ──────────────────────────────────────────────────────────


def test_문턱을_모르면_단정하지_않는다():
    """**우리 보드가 지금 이 상태다.** 릴레이 모듈 데이터시트를 아직 못 찾았다."""
    findings = r15.check(_ctx())
    assert len(findings) == 1
    f = findings[0]
    assert f.verdict is Verdict.UNRESOLVED
    assert "확인해야 합니다" in f.claim
    assert f.unresolved_reason and "V_IH" in f.suggestion


def test_상대가_입력인지_단정하지_않는다():
    """넷리스트에는 핀 방향이 없다. 조건절로 적는다 (헌법 11절)."""
    f = r15.check(_ctx())[0]
    assert "받는다면" in f.claim, f.claim


def test_펌웨어가_없으면_아무_말도_하지_않는다():
    graph = Graph(parse_any(NETLIST))
    assert r15.check(Context(netlist=graph)) == []


# ── 실측 보드 v2 — 실제로 보고된 증상과 같은 자리 ────────────────────


def test_실측_보드_v2_에서_릴레이_핀을_짚는다():
    """보고된 증상: "LED가 ON은 되는데 OFF가 안된다".

    R15 가 그 네트(`_IN_ACTIVE_LOW`)를 짚는다. **원인이라고 단정하지는 않는다** —
    `vih_min` 을 아직 모르므로 UNRESOLVED 다. 확인되면 그때 확정되거나 해제된다.
    """
    from prefab.firmware import load_directory
    from prefab.runner import analyze

    a = analyze(
        (FIXTURES / "esp32-c6-presence-smart-light.d356").read_text(encoding="utf-8"),
        filename="b.d356",
        bom_bytes=(FIXTURES / "esp32-c6-presence-smart-light.bom.csv").read_bytes(),
        firmware_sources=load_directory(FIXTURES / "esp32-c6-presence-smart-light.v2.firmware"),
    )
    found = [f for f in a.engine.findings if f.rule == "R15"]
    assert len(found) == 1, [f.rule for f in a.engine.findings]
    assert found[0].net == "_IN_ACTIVE_LOW"
    assert found[0].verdict is Verdict.UNRESOLVED
