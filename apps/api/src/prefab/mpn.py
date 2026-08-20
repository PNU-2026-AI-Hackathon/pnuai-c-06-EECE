"""부품번호를 어디서 아는가 — 출처를 잃지 않고 한 자리에 모은다.

부품번호가 들어오는 길이 **두 개**가 됐다.

    BOM CSV        사람이 직접 적은 것
    회로도 넷리스트  도구가 심볼 필드에서 실어 준 것 (kicadxml)

전에는 BOM 하나뿐이라 `bom.mpns` 를 여기저기서 그냥 읽었다. 이제는 두 길이 있고,
**어느 쪽에서 왔는지가 판정 문구에 남아야 한다** — 사람이 적은 값과 도구가 실어 준
값은 틀렸을 때 고치는 자리가 다르다. BOM 이 틀리면 BOM 을 고치고, 회로도가 틀리면
심볼 필드를 고친다. "부품번호 미상"만 띄우면 사용자가 어디를 봐야 할지 모른다.

**BOM 이 먼저다.** 사람이 직접 적은 것이 도구가 자동으로 채운 것보다 세다 —
BOM 을 낸 사람은 그 보드에 실제로 무엇을 붙일지 정한 사람이다.
회로도는 BOM 이 없거나 BOM 이 빠뜨린 부품을 채운다.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from .bom import Bom
from .netlist.d356 import Netlist
from .netlist.kicadxml import SchematicNetlist

#: 출처 id → 사람이 읽는 이름. 판정 문구와 파이프라인이 같이 쓴다.
SOURCE_NAMES = {"bom": "BOM", "schematic": "회로도"}


@dataclass(frozen=True)
class PartNumber:
    """부품 하나의 부품번호와 **그것을 어디서 알았는지.**"""

    refdes: str
    mpn: str
    #: `bom` 또는 `schematic`
    source: str

    @property
    def source_name(self) -> str:
        return SOURCE_NAMES.get(self.source, self.source)


def part_numbers(netlist: Netlist, bom: Bom | None) -> "OrderedDict[str, PartNumber]":
    """넷리스트에 실제로 있는 부품에 대해서만 부품번호를 모은다.

    **넷리스트에 없는 BOM 행은 세지 않는다.** 그건 BOM↔회로도 어긋남이고
    `Bom.match()` 가 따로 보고한다 — 여기서 부품 수를 부풀리면 안 된다.
    """
    on_board = set(netlist.parts)
    out: "OrderedDict[str, PartNumber]" = OrderedDict()

    if bom is not None:
        for refdes, row in bom.rows.items():
            if refdes in on_board and row.mpn:
                out[refdes] = PartNumber(refdes, row.mpn, "bom")

    # 회로도가 채우는 것은 **BOM 이 말하지 않은 부품뿐이다.**
    if isinstance(netlist, SchematicNetlist):
        for refdes, part in netlist.components.items():
            if refdes in on_board and part.mpn and refdes not in out:
                out[refdes] = PartNumber(refdes, part.mpn, "schematic")

    return out


def known_mpns(netlist: Netlist, bom: Bom | None) -> list[str]:
    """사실 DB 를 두드릴 부품번호들. 중복을 없애고 정렬한다."""
    return sorted({p.mpn for p in part_numbers(netlist, bom).values()})


def sources_used(numbers: "OrderedDict[str, PartNumber]") -> "OrderedDict[str, int]":
    """출처별 개수. 파이프라인이 "어디서 몇 개를 알았는지" 를 적는 데 쓴다."""
    counts: "OrderedDict[str, int]" = OrderedDict()
    for p in numbers.values():
        counts[p.source] = counts.get(p.source, 0) + 1
    return counts
