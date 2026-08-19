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


# ── 계층 시트 경로 (A+1) ────────────────────────────────────────────


def test_계층_경로가_붙어도_접지는_접지다():
    """KiCad 는 계층 시트를 쓰면 네트 이름 앞에 경로를 붙인다 — `/GND`.

    이름 패턴이 `^` 로 시작해서 **접지가 접지로 안 보였다.** 실제 오픈소스 보드에서
    `/GND` 가 신호 네트로 분류되고 있었고, 그러면 그 위에 도는 규칙이 전부 흔들린다.
    Flux 로 만든 우리 픽스처는 경로가 없어서 이 문제를 한 번도 못 만났다.
    """
    from prefab.netlist.graph import GND_PATTERN, local_name

    for net in ("/GND", "/Sensor/GND", "GND", "GND_BUS"):
        assert GND_PATTERN.match(local_name(net)), net
    for net in ("/PRESENCE_3V3", "SIG"):
        assert not GND_PATTERN.match(local_name(net)), net


def test_공급핀이_둘_이상이면_이름_없이도_전원_레일이다():
    """`V_LDO` 처럼 전압 토큰도 `+` 도 없는 레일이 있다. 토폴로지가 말해 준다."""
    from prefab.netlist.d356 import parse_text
    from prefab.netlist.graph import Graph
    from tests._builder import board, rec

    text = board(
        rec("ANON_RAIL", "U1", "VCC", x=0.0),
        rec("ANON_RAIL", "U2", "VDD", x=0.1),
        rec("ANON_RAIL", "U3", "IN", x=0.2),
        rec("SIG", "U1", "OUT", x=0.3),
        rec("SIG", "U2", "IN", x=0.4),
    )
    g = Graph(parse_text(text))
    assert g.is_power_rail("ANON_RAIL")
    assert not g.is_power_rail("SIG")


def test_이름이_레일_같아도_증거가_없으면_신호다():
    """`PRESENCE_3V3` 는 이름에 전압이 있지만 센서 출력이다. 여기서 오탐이 시작된다."""
    from prefab.netlist.d356 import parse_text
    from prefab.netlist.graph import Graph
    from tests._builder import board, rec

    text = board(
        rec("PRESENCE_3V3", "U2", "OUT", x=0.0),
        rec("PRESENCE_3V3", "U1", "LP-G", x=0.1),
    )
    assert not Graph(parse_text(text)).is_power_rail("PRESENCE_3V3")
