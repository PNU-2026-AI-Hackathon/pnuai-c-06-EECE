"""IPC-D-356 파서 — 실제 파일과 합성 파일 양쪽."""

from __future__ import annotations

from pathlib import Path

from prefab.netlist.d356 import NO_CONNECT, NetlistParseError, parse, parse_text

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
