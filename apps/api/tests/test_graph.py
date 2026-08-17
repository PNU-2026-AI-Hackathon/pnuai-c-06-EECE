"""부품 그래프와 전원 도메인 추론."""

from __future__ import annotations

from pathlib import Path

from prefab.netlist.d356 import parse, parse_text
from prefab.netlist.graph import CONFIDENCE_HIGH, CONFIDENCE_INFERRED, Graph, volts

from _builder import board, rec

FIXTURE = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"


def test_volts_reads_voltage_tokens():
    assert volts("5V_BUS") == 5.0
    assert volts("PRESENCE_3V3") == 3.3
    assert volts("VDD_1V8") == 1.8
    assert volts("_IN_ACTIVE_LOW") is None
    assert volts("SDIO") is None


def test_io_rail_pin_beats_vcc_pin():
    """U1 은 5V 도 받지만 IO 는 3V3 다. 3V3 핀이 이긴다."""
    graph = Graph(parse(FIXTURE))
    u1 = graph.domain("U1")
    assert u1.volts == 3.3
    assert u1.confidence == CONFIDENCE_HIGH


def test_unnamed_pads_fall_back_to_x_cluster():
    """K1 의 패드는 이름이 전부 'pad-'다. 기하가 이름이 잃은 것을 복원한다."""
    graph = Graph(parse(FIXTURE))
    k1 = graph.domain("K1")
    assert k1.volts == 5.0
    assert k1.confidence == CONFIDENCE_INFERRED


def test_k1_pads_split_into_two_physical_groups():
    """제어부와 스위치부. 골든 조건이다."""
    graph = Graph(parse(FIXTURE))
    assert len(graph.clusters("K1")) == 2


def test_passives_get_no_domain():
    graph = Graph(parse(FIXTURE))
    assert not graph.domain("R3").known
    assert "R3" not in graph.domains()


def test_power_rail_is_not_a_signal_net():
    """전압 이름 + 팬아웃이 많으면 신호가 아니라 레일이다."""
    graph = Graph(parse(FIXTURE))
    signals = graph.signal_nets()
    assert "5V_BUS" not in signals
    assert "GND_BUS" not in signals
    assert "PRESENCE_3V3" in signals


def test_supply_pin_of_returns_none_for_unnamed_pads():
    graph = Graph(parse(FIXTURE))
    assert graph.supply_pin_of("K1") is None
    assert graph.supply_pin_of("U2") == ("VCC", "5V_BUS")


def test_domain_unknown_when_no_rail_is_visible():
    text = board(
        rec("SIG", "U9", "OUT"),
        rec("SIG", "U8", "IN"),
    )
    graph = Graph(parse_text(text))
    assert not graph.domain("U9").known
    assert graph.domain("U9").basis == "unknown"
