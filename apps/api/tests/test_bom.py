"""BOM CSV 파서.

넷리스트에는 부품번호가 하나도 없다. BOM 이 트랙 B(데이터시트 축) 전체의 입구다.
읽다가 버린 것을 전부 보고하는지가 이 파서의 핵심이다 (CLAUDE.md 2-4).
"""

from __future__ import annotations

import pytest

from prefab.bom import BomParseError, normalize_mpn, parse_bytes, parse_text


def test_basic_columns():
    b = parse_text("Reference,MPN,Manufacturer,Value\nU1,ESP32-C6-WROOM-1,Espressif,\n")
    assert len(b) == 1
    row = b.rows["U1"]
    assert row.mpn == "ESP32-C6-WROOM-1"
    assert row.manufacturer == "Espressif"
    assert b.mpn_of("u1") == "ESP32-C6-WROOM-1"      # 대소문자 무관


def test_header_aliases_across_tools():
    """도구마다 열 이름이 다르다. Altium 은 Designator, 국문 엑셀은 부품번호."""
    b = parse_text("Designator,Part Number\nR1,RC0402FR-071KL\n")
    assert b.mpn_of("R1") == "RC0402FR-071KL"

    b2 = parse_text("부품기호,부품번호,제조사\nC1,CL10B104KB8NNNC,Samsung\n")
    assert b2.mpn_of("C1") == "CL10B104KB8NNNC"


def test_one_row_can_cover_many_parts():
    """실제 BOM 은 같은 부품을 한 행에 몰아 적는다."""
    b = parse_text('Reference,MPN\n"C1, C2, C3",CL10B104\n')
    assert sorted(b.rows) == ["C1", "C2", "C3"]
    assert all(b.mpn_of(r) == "CL10B104" for r in ("C1", "C2", "C3"))


def test_blank_mpn_is_reported_not_silently_dropped():
    """행은 있는데 번호가 없는 것과 행 자체가 없는 것은 다르다."""
    b = parse_text("Reference,MPN\nU1,ESP32\nK1,\n")
    assert b.mpn_of("K1") is None
    assert any("빈 행" in n for n in b.parse_notes())


def test_match_looks_both_ways():
    """BOM 에만 있는 부품은 BOM 과 회로도가 어긋났다는 뜻이다. 그냥 넘기지 않는다."""
    b = parse_text("Reference,MPN\nU1,ESP32\nK1,\nU9,SOMETHING\n")
    m = b.match(["U1", "K1", "R3"])
    assert m.identified == ["U1"]
    assert m.blank_mpn == ["K1"]
    assert m.missing_in_bom == ["R3"]
    assert m.extra_in_bom == ["U9"]       # 회로도에 없는 부품
    assert m.identified_count == 1


def test_excel_cp949_is_read_not_mangled():
    """한국어 윈도우 엑셀은 CSV 를 CP949 로 저장한다. UTF-8 만 가정하면 깨진다."""
    data = "부품기호,부품번호,제조사\nU1,ESP32-C6,에스프레시프\n".encode("cp949")
    b = parse_bytes(data)
    assert b.mpn_of("U1") == "ESP32-C6"
    assert b.rows["U1"].manufacturer == "에스프레시프"
    assert any("cp949" in n.lower() for n in b.parse_notes())


def test_utf8_bom_from_excel():
    """엑셀은 UTF-8 로 저장해도 앞에 BOM 바이트를 붙인다."""
    b = parse_bytes("Reference,MPN\nU1,ESP32\n".encode("utf-8-sig"))
    assert b.mpn_of("U1") == "ESP32"


def test_missing_required_columns_fails_loudly():
    with pytest.raises(BomParseError) as e:
        parse_text("이름,수량\n저항,3\n")
    assert "부품번호" in str(e.value)


def test_empty_file_fails_loudly():
    with pytest.raises(BomParseError):
        parse_text("")


def test_normalize_strips_annotation_but_does_not_guess():
    """괄호 주석은 뗀다. 메모리 옵션 같은 접미사는 **추측하지 않는다.**

    어디까지가 기본 품번인지는 벤더마다 다르다. 잘못 자르면 없는 부품을 찾게 된다.
    """
    assert normalize_mpn("HLK-LD2410C  (5V)") == "HLK-LD2410C"
    assert normalize_mpn("  ESP32   C6  ") == "ESP32 C6"
    # 접미사는 그대로 둔다
    assert normalize_mpn("ESP32-C6-WROOM-1-N8") == "ESP32-C6-WROOM-1-N8"


def test_raw_mpn_is_kept_for_audit():
    """정규화가 틀렸을 때 되짚을 수 있어야 한다."""
    b = parse_text("Reference,MPN\nU2,HLK-LD2410C (5V)\n")
    assert b.rows["U2"].mpn == "HLK-LD2410C"
    assert b.rows["U2"].mpn_raw == "HLK-LD2410C (5V)"


# ---------------------------------------------------------------- 끝까지 도는가

#: **합성 BOM 이다.** 팀이 준 실제 BOM 이 아니다.
#: U2 를 일부러 비워 두었다 — 지금 그 부품을 정말 모르기 때문이다.
_SYNTHETIC_BOM = (
    "Reference,MPN,Manufacturer\n"
    "U1,XIAO-ESP32C6,Seeed\n"
    "U2,,\n"
    "K1,JQC-3FF-S-Z,Tongling\n"
    '"C1,C2",CL10B104KB8NNNC,Samsung\n'
    '"R1,R2,R3",RC0402FR-0710KL,Yageo\n'
)


def test_real_board_with_bom_identifies_parts(tmp_path):
    from pathlib import Path

    from prefab.report import build_result
    from prefab.runner import analyze

    fixture = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"
    a = analyze(fixture.read_text(), filename=fixture.name,
                bom_bytes=_SYNTHETIC_BOM.encode())

    result = build_result(
        check_id="chk_test", created_at="2026-08-19T00:00:00Z",
        netlist=a.netlist, engine=a.engine, netlist_filename=fixture.name,
        bom_filename="bom.csv", bom=a.bom,
    )
    s = result["summary"]
    # U1 · K1 · C1 · C2 · R1 · R2 · R3 = 7. U2 는 번호가 비었고 J1 · J2 는 행이 없다.
    assert s["parts_identified"] == 7
    assert s["parts_total"] == 10

    detail = result["pipeline"][1]["detail"]
    assert "7/10 식별" in detail
    assert "U2" in detail          # 번호 빈 칸으로 보고
    assert "J1" in detail          # BOM 에 행이 없다고 보고


def test_bom_without_bom_keeps_zero():
    """BOM 을 안 주면 식별 0. 있는 척하지 않는다."""
    from pathlib import Path

    from prefab.report import build_result
    from prefab.runner import analyze

    fixture = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"
    a = analyze(fixture.read_text(), filename=fixture.name)
    result = build_result(
        check_id="c", created_at="t", netlist=a.netlist, engine=a.engine,
        netlist_filename=fixture.name, bom=a.bom,
    )
    assert result["summary"]["parts_identified"] == 0
    assert result["inputs"]["bom"] is None
