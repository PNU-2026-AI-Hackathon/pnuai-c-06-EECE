"""R12 — 양성 / 음성 / 미해결."""

from __future__ import annotations

from prefab.netlist.d356 import parse_text
from prefab.netlist.graph import Graph
from prefab.rules import r12_cross_domain as r12
from prefab.types import Severity, Verdict

from _builder import board, rec
from prefab.types import Context


def _run(text: str):
    return r12.check(Context(netlist=Graph(parse_text(text))))


def test_positive_five_volt_part_drives_a_three_volt_part():
    text = board(
        rec("5V_BUS", "U2", "VCC"),
        rec("PRESENCE", "U2", "OUT"),
        rec("3V3", "U1", "3V3"),
        rec("PRESENCE", "U1", "IN"),
    )
    findings = _run(text)
    assert [f.rule for f in findings] == ["R12"]
    f = findings[0]
    assert f.severity is Severity.CRITICAL
    assert "직렬 저항도 분압도 레벨 시프터도 없습니다" in f.claim
    assert f.evidence[0].highlight[0] == "5V_BUS"


def test_negative_same_domain_on_both_ends():
    text = board(
        rec("3V3", "U2", "VCC"),
        rec("PRESENCE", "U2", "OUT"),
        rec("3V3", "U1", "3V3"),
        rec("PRESENCE", "U1", "IN"),
    )
    assert _run(text) == []


def test_negative_needs_two_parts_with_known_domains():
    text = board(
        rec("5V_BUS", "U2", "VCC"),
        rec("PRESENCE", "U2", "OUT"),
        rec("PRESENCE", "J9", "1"),  # J9 는 전원 도메인을 알 수 없다
    )
    assert _run(text) == []


def test_pullup_is_not_counted_as_series_protection():
    """풀업 저항이 있다고 안전해지지 않는다. 오탐이 아니라 진짜 구분이다."""
    text = board(
        rec("5V_BUS", "K1", "VCC"),
        rec("RELAY_IN", "K1", "OUT"),
        rec("RELAY_IN", "R3", "P1"),
        rec("3V3", "R3", "P2"),
        rec("3V3", "U1", "3V3"),
        rec("RELAY_IN", "U1", "IN"),
    )
    findings = _run(text)
    assert len(findings) == 1
    assert "풀업" in findings[0].claim
    assert "3V3" in findings[0].claim  # 반대쪽 터미널을 실제로 봤다는 증거
    assert "직렬로 옮기지 않는 한" in findings[0].suggestion


def test_unresolved_when_the_driver_cannot_be_identified():
    """BOM 이 없으면 Voh 를 못 읽는다. 판정을 확정하지 않고 이유를 남긴다."""
    text = board(
        rec("5V_BUS", "U2", "VCC"),
        rec("PRESENCE", "U2", "OUT"),
        rec("3V3", "U1", "3V3"),
        rec("PRESENCE", "U1", "IN"),
    )
    f = _run(text)[0]
    assert f.verdict is Verdict.FAIL
    # 무엇을 하면 풀리는지까지 말한다. "BOM 필요" 만으로는 다음에 뭘 할지 모른다.
    assert f.unresolved_reason == "U2 미식별 — BOM 을 제출하면 출력 하이 전압(Voh)을 확인합니다"
    assert "Voh" in f.suggestion
    assert "3.6V" in f.suggestion


def test_pulldown_is_not_called_a_pullup():
    """요청서 2-6 / A-1 — 저항 반대쪽이 GND 면 풀다운이다.

    반대쪽을 안 보고 전부 "pull-up" 이라고 쓰던 버그. 실제 보드의 R3 는 진짜 풀업이라
    그 보드만 돌려서는 안 보인다. 그래서 합성 픽스처가 따로 있다.
    """
    text = board(
        rec("5V_BUS", "U2", "VCC"),
        rec("SIG", "U2", "OUT"),
        rec("SIG", "R1", "P1"),
        rec("GND_BUS", "R1", "P2"),
        rec("3V3", "U1", "3V3"),
        rec("SIG", "U1", "IN"),
    )
    f = _run(text)[0]
    assert "풀다운" in f.claim
    assert "풀업" not in f.claim


def test_real_board_resistor_is_still_a_pullup():
    """실제 보드 R3 는 3V3 로 가는 진짜 풀업이다. 고치면서 이쪽이 뒤집히면 안 된다."""
    from pathlib import Path

    from prefab.netlist.d356 import parse

    fixture = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"
    findings = r12.check(Context(netlist=Graph(parse(fixture))))
    relay = next(f for f in findings if f.net == "_IN_ACTIVE_LOW")
    assert "풀업" in relay.claim and "풀다운" not in relay.claim


def test_divider_is_not_flagged():
    """직렬 저항이 네트를 끊으면 교차 도메인이 성립하지 않는다. 오탐이면 안 된다."""
    from pathlib import Path

    from prefab.netlist.d356 import parse

    fixture = Path(__file__).parent / "fixtures" / "synthetic-divider-vs-pulldown.d356"
    findings = r12.check(Context(netlist=Graph(parse(fixture))))
    assert [f.net for f in findings] == ["SIG_A"]  # SIG_B(분압)는 조용해야 한다


def test_direction_is_only_claimed_when_the_pin_name_says_so():
    """A-2 — `pad-` 처럼 이름 없는 패드에서는 누가 구동하는지 알 수 없다."""
    named = board(
        rec("5V_BUS", "U2", "VCC"),
        rec("SIG", "U2", "OUT"),
        rec("3V3", "U1", "3V3"),
        rec("SIG", "U1", "IN"),
    )
    assert "출력" in _run(named)[0].claim

    unnamed = board(
        rec("5V_BUS", "K1", "pad-", x=0.0),
        rec("GND_BUS", "K1", "pad-", x=0.01),
        rec("SIG", "K1", "pad-", x=0.02),
        rec("3V3", "U1", "3V3", x=5.0),
        rec("SIG", "U1", "IN", x=5.0),
    )
    claim = _run(unnamed)[0].claim
    assert "출력" not in claim
    assert "같은 네트에 직결" in claim


def test_inferred_domain_is_worded_as_an_estimate():
    """이름 없는 패드에서 추론한 도메인은 '추정'이라고 쓴다. 단정하지 않는다."""
    text = board(
        rec("5V_BUS", "K1", "pad-", x=0.0),
        rec("GND_BUS", "K1", "pad-", x=0.01),
        rec("RELAY_IN", "K1", "pad-", x=0.02),
        rec("3V3", "U1", "3V3", x=5.0),
        rec("RELAY_IN", "U1", "IN", x=5.0),
    )
    findings = _run(text)
    assert len(findings) == 1
    assert "5V로 추정되는 K1" in findings[0].claim


def test_check_is_a_pure_function():
    text = board(
        rec("5V_BUS", "U2", "VCC"),
        rec("PRESENCE", "U2", "OUT"),
        rec("3V3", "U1", "3V3"),
        rec("PRESENCE", "U1", "IN"),
    )
    assert [f.to_dict() for f in _run(text)] == [f.to_dict() for f in _run(text)]
