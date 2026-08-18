"""R11 — 양성 / 음성 / 미해결."""

from __future__ import annotations

from prefab.netlist.d356 import parse_text
from prefab.netlist.graph import Graph
from prefab.rules import r11_net_name_domain as r11
from prefab.types import Context, Verdict

from _builder import board, rec


def _run(text: str):
    return r11.check(Context(netlist=Graph(parse_text(text))))


def test_positive_net_name_lies_about_the_domain():
    """이름은 3V3인데 구동부는 5V로 돈다."""
    text = board(
        rec("5V_BUS", "U2", "VCC"),
        rec("SENSE_3V3", "U2", "OUT"),
        rec("3V3", "U1", "3V3"),
        rec("SENSE_3V3", "U1", "IN"),
    )
    findings = _run(text)
    assert [f.rule for f in findings] == ["R11"]
    f = findings[0]
    assert f.net == "SENSE_3V3"
    assert "3.3V" in f.claim and "5V" in f.claim
    assert f.evidence[0].kind == "netlist"
    assert "5V_BUS" in f.evidence[0].highlight


def test_negative_net_name_matches_the_domain():
    """이름도 3V3, 구동부도 3V3. 아무 말도 하지 않는다."""
    text = board(
        rec("3V3", "U2", "VCC"),
        rec("SENSE_3V3", "U2", "OUT"),
        rec("3V3", "U1", "3V3"),
        rec("SENSE_3V3", "U1", "IN"),
    )
    assert _run(text) == []


def test_negative_net_without_voltage_token_is_ignored():
    text = board(
        rec("5V_BUS", "U2", "VCC"),
        rec("PRESENCE", "U2", "OUT"),
        rec("3V3", "U1", "3V3"),
        rec("PRESENCE", "U1", "IN"),
    )
    assert _run(text) == []


def test_unresolved_domain_produces_no_finding_and_no_guess():
    """구동부 전원을 못 읽으면 추측해서 FAIL 을 내지 않는다 (CLAUDE.md 2-2)."""
    text = board(
        rec("SENSE_3V3", "U2", "OUT"),  # U2 의 전원 핀이 어디에도 없다
        rec("3V3", "U1", "3V3"),
        rec("SENSE_3V3", "U1", "IN"),
    )
    assert _run(text) == []


def test_finding_carries_the_reason_it_is_not_final():
    """발견은 냈지만 부품을 식별 못 했다는 사실을 남긴다."""
    text = board(
        rec("5V_BUS", "U2", "VCC"),
        rec("SENSE_3V3", "U2", "OUT"),
        rec("3V3", "U1", "3V3"),
        rec("SENSE_3V3", "U1", "IN"),
    )
    f = _run(text)[0]
    assert f.verdict is Verdict.FAIL
    assert f.unresolved_reason == "U2 미식별 — BOM 을 제출하면 출력 하이 전압(Voh)을 확인합니다"
    assert f.suggestion


def test_check_is_a_pure_function():
    """같은 입력이면 항상 같은 결과. 이게 깨지면 제품이 죽는다."""
    text = board(
        rec("5V_BUS", "U2", "VCC"),
        rec("SENSE_3V3", "U2", "OUT"),
        rec("3V3", "U1", "3V3"),
        rec("SENSE_3V3", "U1", "IN"),
    )
    first = [f.to_dict() for f in _run(text)]
    second = [f.to_dict() for f in _run(text)]
    assert first == second
