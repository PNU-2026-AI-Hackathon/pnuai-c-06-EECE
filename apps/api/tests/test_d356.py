"""IPC-D-356 파서 — 실제 파일과 합성 파일 양쪽."""

from __future__ import annotations

from pathlib import Path

from prefab.netlist.d356 import (
    NET_NAME_WIDTH,
    NO_CONNECT,
    NetlistParseError,
    parse,
    parse_text,
)
from tests._builder import board, rec

from _builder import board, rec, via

FIXTURE = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"


def test_real_board_counts():
    nl = parse(FIXTURE)
    assert nl.net_count == 8
    assert nl.part_count == 10
    assert sorted(nl.parts) == ["C1", "C2", "J1", "J2", "K1", "R1", "R2", "R3", "U1", "U2"]


def test_pin_names_are_truncated_to_four_chars():
    """이 형식의 가장 중요한 한계. 정확한 GPIO 번호를 알 수 없는 이유다."""
    nl = parse(FIXTURE)
    assert "LP-G" in nl.parts["U1"]  # LP-GPIO0 이 잘린 것
    assert max(len(p) for pins in nl.parts.values() for p in pins) == 4


def test_vias_are_counted_but_not_connections():
    nl = parse(FIXTURE)
    assert nl.via_count("GND_BUS") == 2
    assert all(ref != "VIA" for ref, _pin in nl.connections("GND_BUS"))


def test_no_connect_bucket_is_excluded_from_net_count():
    text = board(
        rec("SIG_A", "U1", "OUT"),
        rec("SIG_A", "U2", "IN"),
        rec(NO_CONNECT, "U1", "NC1"),
    )
    nl = parse_text(text)
    assert nl.net_count == 1
    assert NO_CONNECT in nl.nets  # 버리지는 않는다. 세지 않을 뿐이다


def test_synthetic_records_use_the_same_offsets_as_the_real_file():
    """합성 픽스처가 진짜 파일과 같은 자리를 쓰는지 확인한다."""
    line = rec("PRESENCE_3V3", "U2", "OUT", x=1.2345, y=-0.5)
    assert line[0:3] == "327"
    assert line[3:17].strip() == "PRESENCE_3V3"
    assert line[20:26].strip() == "U2"
    assert line[26] == "-"
    assert line[27:31].strip() == "OUT"
    nl = parse_text(board(line))
    pad = nl.nets["PRESENCE_3V3"][0]
    assert (round(pad.x, 4), round(pad.y, 4)) == (1.2345, -0.5)


def test_crlf_file_parses():
    text = board(rec("SIG", "U1", "OUT"), rec("SIG", "U2", "IN")).replace("\n", "\r\n")
    assert parse_text(text).net_count == 1


def test_garbage_file_raises_parse_error():
    try:
        parse_text("이건 넷리스트가 아닙니다\n그냥 텍스트\n")
    except NetlistParseError as exc:
        assert "IPC-D-356" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("NetlistParseError 가 나와야 한다")


def test_ordered_net_names_puts_busiest_first():
    nl = parse(FIXTURE)
    assert nl.ordered_net_names()[0] == "GND_BUS"
    assert nl.ordered_net_names()[1] == "5V_BUS"


# ---------------------------------------------------------------- 도구별 차이
#
# 같은 IPC-D-356 인데 도구마다 내보내는 것이 다르다. 실측으로 확인한 것:
#   Flux   핀 이름(VBUS · GND_) · 317/327 만
#   KiCad  패드 번호(1 · 2 · 3) · 비도금 홀을 367 로
#   Eagle  핀 이름 · 홀을 347 로 (ULP 소스 확인)
# 전부 P UNITS CUST 0 (인치) 을 쓴다.


def test_kicad_non_electrical_records_are_reported_not_silently_dropped():
    """KiCad 는 비도금 홀을 367 로 낸다. 빼는 건 맞지만 조용히 빼면 안 된다.

    실제 오픈소스 보드(VhARIO-ESPC3)를 kicad-cli 로 뽑으니 367 이 6줄 나왔다.
    """
    text = "\n".join(
        [
            "P  UNITS CUST 0",
            "317NET1              U1    -1    D0100PA00X+001000Y+001000X0100Y0100R000",
            "327NET1              U2    -2    D0000PA00X+002000Y+001000X0100Y0100R000",
            "367N/C               H1          D0984UA00X+003000Y+001000X0984Y0000R000",
            "999",
        ]
    )
    nl = parse_text(text)
    assert nl.non_electrical == {"367": 1}
    assert nl.unknown_records == {}
    assert "비도금 홀" in " ".join(nl.parse_notes())


def test_unknown_record_type_is_surfaced_as_a_warning():
    """모르는 레코드는 연결을 놓친 것일 수 있다. 반드시 알린다."""
    text = "\n".join(
        [
            "P  UNITS CUST 0",
            "317NET1              U1    -1    D0100PA00X+001000Y+001000X0100Y0100R000",
            "397NET9              U9    -9    D0100PA00X+009000Y+009000X0100Y0100R000",
            "999",
        ]
    )
    nl = parse_text(text)
    assert nl.unknown_records == {"397": 1}
    assert any("모르는 레코드" in n for n in nl.parse_notes())


def test_metric_units_are_rejected_instead_of_silently_misread():
    """미터법을 인치로 읽으면 좌표가 25.4배 틀려 패드 그룹이 잘못 나뉜다.

    지금 아는 도구는 전부 CUST 0 이지만 형식은 미터법을 허용한다.
    조용히 틀리느니 읽기를 거부한다.
    """
    import pytest

    text = "\n".join(
        [
            "P  UNITS CUST 1",
            "317NET1              U1    -1    D0100PA00X+001000Y+001000X0100Y0100R000",
            "999",
        ]
    )
    with pytest.raises(NetlistParseError) as e:
        parse_text(text)
    assert "CUST 1" in str(e.value)


def test_flux_fixture_drops_no_records():
    """Flux 출처 픽스처는 뺄 레코드가 없다. 회귀 감시용."""
    nl = parse(FIXTURE)
    assert nl.non_electrical == {}
    assert nl.unknown_records == {}
    # 뺀 레코드는 없지만 **네트명 절단 경고는 있다** (A++2). 아래 테스트가 그것이다.
    assert not [n for n in nl.parse_notes() if "제외" in n or "모르는 레코드" in n]


# ── 네트명 14자 절단 (A++2) ─────────────────────────────────────────


def test_칸을_꽉_채운_네트명을_찾아낸다():
    """핀 이름이 4자에서 잘리는 것과 같은 문제인데 더 조용하게 아프다."""
    nl = parse(FIXTURE)
    assert nl.width_limited_nets() == ["_IN_ACTIVE_LOW", "D_POS_SWITCHED"]
    assert all(len(n) == NET_NAME_WIDTH for n in nl.width_limited_nets())


def test_절단_가능성을_파싱_노트에_적는다():
    """조용히 넘기면 R11 이 왜 조용한지 아무도 모른다 (헌법 2-4)."""
    note = " ".join(parse(FIXTURE).parse_notes())
    assert "꽉 참" in note and "잘렸을 수 있습니다" in note
    assert "_IN_ACTIVE_LOW" in note


def test_짧은_이름은_아무_말도_안_한다():
    """정상 보드에서 이 경고가 뜨면 노이즈다."""
    nl = parse_text(board(rec("3V3", "U1", "VCC"), rec("3V3", "C1", "P1", x=0.1)))
    assert nl.width_limited_nets() == []
    assert nl.parse_notes() == []


def test_잘렸다고_단정하지_않는다():
    """딱 14자인 이름을 지었을 수도 있다. 말할 수 있는 건 '못 믿는다' 까지다."""
    note = " ".join(parse(FIXTURE).parse_notes())
    assert "잘렸습니다" not in note
    assert "수 있습니다" in note
