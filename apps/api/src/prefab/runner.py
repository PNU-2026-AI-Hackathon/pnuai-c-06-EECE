"""입력 → 파싱 → 그래프 → 규칙 엔진. 한 줄로 부르는 자리.

CLI 와 web 이 같은 함수를 쓴다. 두 벌을 만들지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from .datasheet import Bom
from .datasheet import parse_text as parse_bom
from .engine import EngineResult, run
from .firmware import Firmware
from .firmware import analyze as analyze_firmware
from .netlist.d356 import Netlist, parse_text
from .netlist.graph import Graph
from .types import Context


@dataclass(frozen=True)
class Analysis:
    netlist: Netlist
    graph: Graph
    engine: EngineResult
    firmware: Firmware | None = None
    bom: Bom | None = None

    def to_netlist_dict(self) -> dict:
        return self.netlist.to_dict(self.graph.pinmap, self.bom)

    @property
    def parts_identified(self) -> int:
        """부품번호까지 확정된 부품 수. 넷리스트에 있는 것만 센다."""
        if self.bom is None:
            return 0
        known, _unknown = self.bom.coverage(set(self.netlist.parts))
        return len(known)


def analyze(
    netlist_text: str,
    *,
    filename: str = "",
    bom_text: str | None = None,
    bom_filename: str = "",
    firmware_sources: "dict[str, str] | None" = None,
) -> Analysis:
    """넷리스트 본문(+ 있으면 펌웨어 소스)을 받아 검사까지 끝낸다.

    BOM 이 있으면 부품번호까지 읽는다. 다만 그 부품번호로 **데이터시트를 읽는 단계는
    아직 없다** — 그래서 datasheet 를 NEEDS 로 선언한 규칙은 여전히 건너뛴다.
    있는 척하지 않는다.
    """
    netlist = parse_text(netlist_text, filename=filename)
    graph = Graph(netlist)

    firmware = analyze_firmware(firmware_sources) if firmware_sources else None
    bom = parse_bom(bom_text, filename=bom_filename) if bom_text else None

    ctx = Context(netlist=graph, bom=bom, firmware=firmware)
    return Analysis(
        netlist=netlist, graph=graph, engine=run(ctx), firmware=firmware, bom=bom
    )
