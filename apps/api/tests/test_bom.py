"""BOM CSV 파서 — 도구마다 다른 열 이름을 흡수하고, 못 읽은 행은 남긴다."""

from __future__ import annotations

from pathlib import Path

import pytest

from prefab.datasheet import Bom, BomParseError, parse, parse_text

FIXTURE = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.bom.csv"


def test_real_bom_identifies_the_three_modules():
    bom = parse(FIXTURE)
    assert len(bom) == 10
    assert bom.mpn_of("U2") == "HLK-LD2410C"
    assert bom.mpn_of("K1") == "JQC-3FF-S-Z"
    assert bom.get("K1").manufacturer == "TONGLING"


def test_passives_without_mpn_are_kept_but_not_identified():
    """부품번호가 없다고 버리지 않는다. 값은 있으니 들고 있는다."""
    bom = parse(FIXTURE)
    r3 = bom.get("R3")
    assert r3 is not None
    assert r3.value == "10k"
    assert not r3.identified
    assert {e.ref for e in bom.identified} == {"U1", "U2", "K1"}


def test_coverage_counts_against_the_netlist():
    bom = parse(FIXTURE)
    known, unknown = bom.coverage({"U1", "U2", "K1", "R3", "C1"})
    assert known == ["K1", "U1", "U2"]
    assert unknown == ["C1", "R3"]


def test_lookup_is_case_insensitive():
    assert parse(FIXTURE).mpn_of("u2") == "HLK-LD2410C"


def test_column_aliases_cover_other_tools():
    """KiCad 는 Designator, Altium 은 Part Number 로 부른다."""
    bom = parse_text("Designator;Part Number;Mfr\nU7;ABC-123;Acme\n")
    assert bom.mpn_of("U7") == "ABC-123"
    assert bom.get("U7").manufacturer == "Acme"


def test_tab_separated_is_read():
    bom = parse_text("Reference\tMPN\nU9\tXYZ-9\n")
    assert bom.mpn_of("U9") == "XYZ-9"


def test_multiple_refs_in_one_cell_expand():
    """`R1, R2, R3` 를 한 칸에 적는 도구가 있다."""
    bom = parse_text("Reference,MPN\n\"R1, R2, R3\",RC0402\n")
    assert len(bom) == 3
    assert bom.mpn_of("R2") == "RC0402"


def test_range_notation_is_reported_not_expanded():
    """`R1-R3` 를 펼치면 없는 부품을 만들어낸다. 지어내지 않는다."""
    bom = parse_text("Reference,MPN\nR1-R3,RC0402\nU1,ABC\n")
    assert [e.ref for e in bom.entries] == ["U1"]
    assert any("범위" in s.reason for s in bom.skipped)
    assert any("범위" in note for note in bom.notes())


def test_duplicate_refs_are_reported():
    bom = parse_text("Reference,MPN\nU1,A\nU1,B\n")
    assert len(bom) == 1
    assert bom.mpn_of("U1") == "A"  # 첫 번째를 남긴다
    assert any("중복" in s.reason for s in bom.skipped)


def test_rows_without_a_reference_are_reported():
    bom = parse_text("Reference,MPN\n,ORPHAN\nU1,A\n")
    assert len(bom) == 1
    assert any("기호 없음" in s.reason for s in bom.skipped)


def test_missing_reference_column_is_a_clear_error():
    with pytest.raises(BomParseError) as e:
        parse_text("Part,Price\nwidget,100\n")
    assert "기호" in str(e.value)
    assert "Designator" in str(e.value)  # 무엇을 넣어야 하는지 알려준다


def test_empty_file_is_a_clear_error():
    with pytest.raises(BomParseError):
        parse_text("")


def test_header_only_is_a_clear_error():
    with pytest.raises(BomParseError):
        parse_text("Reference,MPN\n")


def test_notes_surface_what_was_not_read():
    bom = parse_text("Reference,MPN\nU1,A\nR1-R3,B\nC1,\n")
    notes = " ".join(bom.notes())
    assert "범위" in notes
    assert "부품번호 없는 항목" in notes


def test_parse_is_a_pure_function():
    text = FIXTURE.read_text(encoding="utf-8")
    a, b = parse_text(text), parse_text(text)
    assert [(e.ref, e.mpn) for e in a.entries] == [(e.ref, e.mpn) for e in b.entries]
