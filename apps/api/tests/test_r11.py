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


# ── 네트명 14자 절단 (A++2) ─────────────────────────────────────────
#
# 넷리스트의 네트명 칸은 14자다. 이름이 그 길이에 꽉 찼고 전압 표기가 끝에 걸쳐
# 있으면 `..._3V` 가 `_3V3` 의 앞부분일 수 있다. 3.3V 를 3V 로 읽고 경고를 내면
# 그게 오탐이다 — 판정을 내리지 않고 무엇을 확인해야 하는지 적는다.


def _clipped_board(net: str) -> str:
    """`net` 을 5V 부품이 구동하는 보드. 이름만 갈아끼운다."""
    return board(
        rec("5V_BUS", "U2", "VCC"), rec("5V_BUS", "C1", "P1", x=0.1),
        rec("5V_BUS", "C2", "P1", x=0.2), rec("5V_BUS", "J1", "VBUS", x=0.3),
        rec(net, "U2", "OUT", y=0.1),
        rec("3V3", "U1", "3V3", x=0.5), rec("3V3", "C3", "P1", x=0.6),
        rec("3V3", "C4", "P1", x=0.7), rec("3V3", "R9", "P1", x=0.8),
        rec(net, "U1", "D2", x=0.5, y=0.1),
    )


def _r11(netlist: str):
    return _run(netlist)


def test_짧은_이름이면_그대로_판정한다():
    """대조군. 12자짜리 이름은 잘릴 수 없으므로 FAIL 이다."""
    f = _r11(_clipped_board("PRESENCE_3V3"))
    assert len(f) == 1
    assert f[0].verdict is Verdict.FAIL
    # BOM 이 없어 U2 미식별 사유는 붙지만, **절단 사유는 붙지 않는다**
    assert "14자" not in (f[0].unresolved_reason or "")


def test_이름이_칸을_꽉_채우고_전압이_끝에_걸치면_판정을_미룬다():
    """`SENSOR_OUT_3V3` 는 14자다. 원래 `SENSOR_OUT_3V3_A` 였을 수도 있다."""
    f = _r11(_clipped_board("SENSOR_OUT_3V3"))
    assert len(f) == 1
    assert f[0].verdict is Verdict.UNRESOLVED
    assert f[0].unresolved_reason is not None
    assert "14자" in f[0].unresolved_reason
    # 무엇을 하면 풀리는지 적는다. "BOM 필요" 같은 거짓말을 하지 않는다.
    assert "전체 이름" in f[0].unresolved_reason


def test_전압_표기가_끝에_없으면_믿는다():
    """`3V3_SENSOR_OUT` 도 14자지만 전압이 앞에 있어 잘린 자리가 아니다."""
    f = _r11(_clipped_board("3V3_SENSOR_OUT"))
    assert len(f) == 1
    assert f[0].verdict is Verdict.FAIL


def test_판정을_미뤄도_근거는_그대로_붙는다():
    """모른다고 해서 아무것도 안 보여주면 사용자가 확인할 자리가 없다."""
    f = _r11(_clipped_board("SENSOR_OUT_3V3"))[0]
    assert f.evidence
    assert "잘렸을 수 있습니다" in f.claim
