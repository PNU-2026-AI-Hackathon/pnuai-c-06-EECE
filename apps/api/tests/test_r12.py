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
    assert "R3는 풀업이라 직렬 보호 역할을 하지 못합니다" in findings[0].claim
    assert "직렬로 옮기는 것만으로는" in findings[0].suggestion


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
    assert f.unresolved_reason == "U2 미식별 — BOM 필요"
    assert "Voh" in f.suggestion
    assert "3.6V" in f.suggestion


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
    assert "추정되는 K1" in findings[0].claim


def test_check_is_a_pure_function():
    text = board(
        rec("5V_BUS", "U2", "VCC"),
        rec("PRESENCE", "U2", "OUT"),
        rec("3V3", "U1", "3V3"),
        rec("PRESENCE", "U1", "IN"),
    )
    assert [f.to_dict() for f in _run(text)] == [f.to_dict() for f in _run(text)]
