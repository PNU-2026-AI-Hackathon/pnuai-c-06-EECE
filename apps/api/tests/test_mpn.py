"""부품번호를 어디서 아는가 — BOM 과 회로도 두 길.

**출처를 잃으면 사용자가 어디를 고쳐야 할지 모른다.** BOM 이 틀리면 BOM 을 고치고
회로도가 틀리면 심볼 필드를 고친다. "부품번호 미상" 한 마디로는 그 둘이 구별되지 않는다.
"""

from __future__ import annotations

from pathlib import Path

from prefab.bom import parse_bytes as parse_bom_bytes
from prefab.mpn import known_mpns, part_numbers, sources_used
from prefab.netlist.detect import parse_any

FIXTURES = Path(__file__).parent / "fixtures"
D356 = FIXTURES / "esp32-c6-presence-smart-light.d356"
BOM = FIXTURES / "esp32-c6-presence-smart-light.bom.csv"
XML = FIXTURES / "schematic-gpio-named.net.xml"


def _xml():
    return parse_any(XML.read_text(encoding="utf-8"))


def _d356():
    return parse_any(D356.read_text(encoding="utf-8"))


# ── 회로도만 ────────────────────────────────────────────────────────


def test_회로도가_실어_준_부품번호를_읽는다():
    numbers = part_numbers(_xml(), None)
    assert numbers["U1"].mpn == "C2913196"
    assert numbers["U1"].source == "schematic"
    assert numbers["R1"].mpn == "RC0402FR-0710KL"


def test_부품번호가_없는_부품은_안_센다():
    """J1 에는 부품번호가 없다. 세면 식별한 척이 된다."""
    assert "J1" not in part_numbers(_xml(), None)


def test_IPC_D356_은_부품번호를_하나도_안_준다():
    """이 형식에는 그 정보가 통째로 없다. BOM 이 없으면 아는 것이 없다."""
    assert part_numbers(_d356(), None) == {}


# ── BOM 만 ──────────────────────────────────────────────────────────


def test_BOM_에서_읽는다():
    bom = parse_bom_bytes(BOM.read_bytes())
    numbers = part_numbers(_d356(), bom)
    assert numbers["U2"].mpn == "HLK-LD2410C"
    assert numbers["U2"].source == "bom"


def test_넷리스트에_없는_BOM_행은_안_센다():
    """BOM↔회로도 어긋남은 `Bom.match()` 가 따로 본다. 여기서 부품 수를 부풀리면 안 된다."""
    bom = parse_bom_bytes(b"Reference,Value,MPN\nU1,x,MPN-1\nZ99,x,MPN-2\n")
    numbers = part_numbers(_d356(), bom)
    assert "Z99" not in numbers


# ── 둘 다 ───────────────────────────────────────────────────────────


def test_BOM_이_회로도보다_세다():
    """사람이 직접 적은 것이 도구가 자동으로 채운 것보다 세다.

    BOM 을 낸 사람은 그 보드에 실제로 무엇을 붙일지 정한 사람이다.
    """
    bom = parse_bom_bytes(b"Reference,Value,MPN\nU1,x,SOMETHING-ELSE\n")
    numbers = part_numbers(_xml(), bom)
    assert numbers["U1"].mpn == "SOMETHING-ELSE"
    assert numbers["U1"].source == "bom"


def test_회로도가_BOM_의_빈자리를_채운다():
    """BOM 이 U1 만 적었어도 R1 은 회로도가 안다."""
    bom = parse_bom_bytes(b"Reference,Value,MPN\nU1,x,SOMETHING-ELSE\n")
    numbers = part_numbers(_xml(), bom)
    assert numbers["R1"].source == "schematic"
    assert sources_used(numbers) == {"bom": 1, "schematic": 1}


# ── 사실 DB 에 넘기는 형태 ──────────────────────────────────────────


def test_조회할_부품번호는_중복없이_정렬된다():
    mpns = known_mpns(_xml(), None)
    assert mpns == sorted(set(mpns))
    assert "C2913196" in mpns


def test_아무_출처도_없으면_빈_목록이다():
    """빈 목록이면 러너가 DB 를 아예 안 두드린다."""
    assert known_mpns(_d356(), None) == []
