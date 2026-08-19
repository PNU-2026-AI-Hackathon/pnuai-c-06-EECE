"""넷리스트 형식 감지.

**확장자를 안 믿는다.** 사용자는 파일 이름을 바꾸고, 계약이 허용하는 `.txt` 는
둘 다일 수 있다. 내용의 첫 글자만 본다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from prefab.netlist import NetlistParseError
from prefab.netlist.detect import detect, format_of, parse_any

FIXTURES = Path(__file__).parent / "fixtures"
D356 = FIXTURES / "esp32-c6-presence-smart-light.d356"
XML = FIXTURES / "schematic-gpio-named.net.xml"


def test_ipc_d356_을_알아본다():
    assert detect(D356.read_text(encoding="utf-8")) == "d356"


def test_kicadxml_을_알아본다():
    assert detect(XML.read_text(encoding="utf-8")) == "kicadxml"


def test_XML_선언이_없어도_export_로_시작하면_알아본다():
    assert detect("<export version='E'><nets/></export>") == "kicadxml"


def test_앞의_공백과_BOM_에_속지_않는다():
    assert detect("﻿\n  <?xml version='1.0'?><export/>") == "kicadxml"


def test_모르면_d356_으로_본다():
    """기존 동작을 유지한다. 새 형식이 기본값을 바꾸지 않는다."""
    assert detect("아무 말") == "d356"


# ── 실제로 읽히는가 ─────────────────────────────────────────────────


def test_같은_함수로_두_형식을_다_읽는다():
    a = parse_any(D356.read_text(encoding="utf-8"), filename=D356.name)
    b = parse_any(XML.read_text(encoding="utf-8"), filename=XML.name)
    assert format_of(a) == "d356"
    assert format_of(b) == "kicadxml"
    assert a.net_count > 0 and b.net_count > 0


def test_XML_인데_kicadxml_이_아니면_d356_으로_안_되돌린다():
    """되돌리면 '레코드 0줄' 같은 엉뚱한 오류가 나서 진짜 원인을 못 찾는다."""
    with pytest.raises(NetlistParseError, match="kicad-cli"):
        parse_any("<?xml version='1.0'?><svg><g/></svg>")


# ── 형식마다 다른 성질 ──────────────────────────────────────────────


def test_회로도_넷리스트는_이름_절단_경고를_내지_않는다():
    """`Net-(U3-LNA_IN)` 은 잘린 게 아니라 원래 그 이름이다.

    IPC-D-356 의 14자 칸 경고를 그대로 물려받으면 **없는 문제를 만든다.**
    """
    b = parse_any(XML.read_text(encoding="utf-8"))
    assert b.width_limited_nets() == []
    assert not any("14자" in note for note in b.parse_notes())


def test_IPC_D356_은_이름_절단_경고를_계속_낸다():
    """실측 보드의 `_IN_ACTIVE_LOW` 는 실제로 앞이 잘려 있다. 이건 없애면 안 된다."""
    a = parse_any(D356.read_text(encoding="utf-8"))
    assert "_IN_ACTIVE_LOW" in a.width_limited_nets()


def test_회로도_넷리스트는_좌표가_없다고_말한다():
    notes = " ".join(parse_any(XML.read_text(encoding="utf-8")).parse_notes())
    assert "좌표 없음" in notes
