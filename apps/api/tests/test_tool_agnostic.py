"""도구 중립성 — Flux 가 아닌 넷리스트에서도 엔진이 눈을 뜨는가.

요청서 트랙 A+ 의 근거는 실제 실험이었다. KiCad 로 뽑은 오픈소스 보드에서 발견 0건이
나왔는데 깨끗해서가 아니라 **못 봐서**였다. 핀 이름이 `VCC` 가 아니라 `1` · `2` 라
전원 핀 정규식이 한 번도 맞지 않았고, 부품 대부분이 도메인 "모름"이 됐다.

여기 픽스처는 그 상황을 합성으로 재현한다. GPL 파일을 리포에 넣지 않기 위해서다.
"""

from __future__ import annotations

from pathlib import Path

from prefab.netlist.d356 import parse, parse_text
from prefab.netlist.graph import (
    CONFIDENCE_INFERRED,
    PAD_CLUSTER_GAP_INCH,
    Graph,
)

from _builder import board, rec

FIXTURE = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"


def _numeric_pin_board(rail: str = "+3V3", fanout: int = 6) -> str:
    """KiCad 식 보드 — 핀 이름이 전부 숫자다."""
    lines = [
        rec(rail, "U3", "1", x=0.0, y=0.5),
        rec("GND", "U3", "2", x=0.1, y=0.5),
        rec("SIG", "U3", "3", x=0.2, y=0.5),
        rec(rail, "U5", "1", x=2.0, y=0.5),
        rec("GND", "U5", "2", x=2.1, y=0.5),
        rec("SIG", "U5", "3", x=2.2, y=0.5),
    ]
    # 레일로 인정받으려면 팬아웃이 넓어야 한다. 디커플링 커패시터로 채운다.
    for i in range(fanout):
        lines.append(rec(rail, f"C{i + 1}", "1", x=3.0 + 0.1 * i, y=0.5))
        lines.append(rec("GND", f"C{i + 1}", "2", x=3.0 + 0.1 * i, y=0.4))
    return board(*lines)


# ------------------------------------------------------------------- A+2

def test_named_rail_without_a_voltage_token_is_still_a_rail():
    """`+VSW` · `+BATT` 는 전압을 모르지만 전원 레일이다. 신호로 세면 오탐이 난다."""
    graph = Graph(parse_text(_numeric_pin_board(rail="+VSW")))
    assert graph.is_power_rail("+VSW")
    assert "+VSW" not in graph.signal_nets()


def test_rail_name_alone_is_not_enough():
    """이름이 레일 같아도 부품이 둘뿐이면 신호다. 이름만으로 판단하지 않는다."""
    text = board(
        rec("VCC_SENSE", "U3", "1", x=0.0, y=0.5),
        rec("VCC_SENSE", "U5", "1", x=1.0, y=0.5),
        rec("GND", "U3", "2", x=0.1, y=0.5),
        rec("GND", "U5", "2", x=1.1, y=0.5),
    )
    graph = Graph(parse_text(text))
    assert not graph.is_power_rail("VCC_SENSE")
    assert "VCC_SENSE" in graph.signal_nets()


def test_ground_is_always_a_rail():
    graph = Graph(parse(FIXTURE))
    assert graph.is_power_rail("GND_BUS")
    assert "GND_BUS" not in graph.signal_nets()


def test_real_board_signal_nets_are_unchanged():
    """도구 중립성을 넣으면서 우리 보드의 판정 대상이 바뀌면 회귀다."""
    graph = Graph(parse(FIXTURE))
    assert set(graph.signal_nets()) == {
        "_IN_ACTIVE_LOW",
        "3V3",
        "D_POS_SWITCHED",
        "PRESENCE_3V3",
        "USB_CC1",
        "USB_CC2",
    }


# ------------------------------------------------------------------- A+1

def test_domain_from_rail_membership_when_pin_names_are_numbers():
    """핀 이름이 `1` · `2` 면 전원 핀 정규식이 못 맞는다. **네트 소속**으로 푼다."""
    graph = Graph(parse_text(_numeric_pin_board()))
    for ref in ("U3", "U5"):
        domain = graph.domain(ref)
        assert domain.known, f"{ref} 도메인을 못 읽었다"
        assert domain.volts == 3.3
        assert domain.confidence == CONFIDENCE_INFERRED


def test_membership_needs_exactly_one_known_rail():
    """레일 둘에 닿아 있으면 어느 쪽이 IO 인지 모른다. 추측하지 않는다."""
    lines = [
        rec("+3V3", "U7", "1", x=0.0, y=0.5),
        rec("+5V", "U7", "2", x=1.0, y=0.5),
        rec("GND", "U7", "3", x=2.0, y=0.5),
    ]
    for i in range(6):
        lines.append(rec("+3V3", f"C{i + 1}", "1", x=3.0 + 0.1 * i, y=0.5))
        lines.append(rec("+5V", f"C{i + 1}", "2", x=3.0 + 0.1 * i, y=0.4))
        lines.append(rec("GND", f"R{i + 1}", "1", x=4.0 + 0.1 * i, y=0.4))
    graph = Graph(parse_text(board(*lines)))
    assert not graph.domain("U7").known


def test_membership_needs_a_ground_return():
    """레일에만 닿고 접지가 없으면 전원을 받는 부품이라고 볼 수 없다."""
    lines = [rec("+3V3", "U7", "1", x=0.0, y=0.5), rec("SIG", "U7", "2", x=1.0, y=0.5)]
    for i in range(6):
        lines.append(rec("+3V3", f"C{i + 1}", "1", x=3.0 + 0.1 * i, y=0.5))
        lines.append(rec("GND", f"C{i + 1}", "2", x=3.0 + 0.1 * i, y=0.4))
    graph = Graph(parse_text(board(*lines)))
    assert not graph.domain("U7").known


def test_named_supply_pin_still_wins():
    """이름이 있으면 이름을 믿는다. 소속 추론은 마지막 수단이다."""
    graph = Graph(parse(FIXTURE))
    assert graph.domain("U2").basis == "U2.VCC → 5V_BUS"


# ------------------------------------------------------------------- A+6

def test_pads_at_header_pitch_stay_one_group():
    """0.1 inch 피치는 한 부품이다. 예전 값(1.0 inch 절대거리)은 이걸 못 지켰다."""
    graph = Graph(parse(FIXTURE))
    assert len(graph.clusters("U2")) == 1  # 5패드 · 0.1 피치
    assert len(graph.clusters("R3")) == 1  # 0.065
    assert len(graph.clusters("J1")) == 1  # 최대 0.154


def test_relay_control_and_switch_sides_still_split():
    """K1 의 두 그룹은 1.437 inch 떨어져 있다. 갈라야 한다."""
    graph = Graph(parse(FIXTURE))
    assert len(graph.clusters("K1")) == 2


def test_gap_threshold_sits_between_the_two_measurements():
    """상수가 실측 사이에 있는지 — 근거 없는 값이 아니라는 확인."""
    assert 0.154 < PAD_CLUSTER_GAP_INCH < 1.437
