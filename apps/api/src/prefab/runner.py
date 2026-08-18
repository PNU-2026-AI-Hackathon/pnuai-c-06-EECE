"""입력 → 파싱 → 그래프 → 규칙 엔진. 한 줄로 부르는 자리.

CLI 와 web 이 같은 함수를 쓴다. 두 벌을 만들지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

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

    def to_netlist_dict(self) -> dict:
        return self.netlist.to_dict(self.graph.pinmap)


def analyze(
    netlist_text: str,
    *,
    filename: str = "",
    bom: object | None = None,
    firmware_sources: "dict[str, str] | None" = None,
) -> Analysis:
    """넷리스트 본문(+ 있으면 펌웨어 소스)을 받아 검사까지 끝낸다.

    bom 은 아직 파서가 없다. None 이 아니면 '입력은 있다'로만 취급하고,
    그 입력을 NEEDS 로 선언한 규칙은 여전히 미구현이라 건너뛴다.
    있는 척하지 않는다.
    """
    netlist = parse_text(netlist_text, filename=filename)
    graph = Graph(netlist)

    firmware = analyze_firmware(firmware_sources) if firmware_sources else None

    ctx = Context(netlist=graph, bom=bom, firmware=firmware)
    return Analysis(netlist=netlist, graph=graph, engine=run(ctx), firmware=firmware)
