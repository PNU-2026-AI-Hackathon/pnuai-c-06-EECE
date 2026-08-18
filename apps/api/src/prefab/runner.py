"""입력 → 파싱 → 그래프 → 규칙 엔진. 한 줄로 부르는 자리.

CLI 와 web 이 같은 함수를 쓴다. 두 벌을 만들지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field

from .bom import Bom, parse_bytes as parse_bom_bytes
from .datasheet.facts import FactSet
from .datasheet.store import FactStore, Lookup
from .engine import EngineResult, run
from .netlist.d356 import Netlist, parse_text
from .netlist.graph import Graph
from .types import Context


@dataclass(frozen=True)
class Analysis:
    netlist: Netlist
    graph: Graph
    engine: EngineResult
    #: BOM 을 받아 읽었으면 그 결과. 안 받았으면 None
    bom: Bom | None = None
    #: 부품 사실 DB 조회 결과. 조회를 안 했으면 None.
    #: `misses` 가 "이 부품들은 아직 데이터시트를 안 읽었다"는 정직한 목록이다.
    facts: Lookup | None = None
    #: 규칙에 실제로 넘어간 입력들. 무엇이 손에 있었는지 나중에 되짚을 수 있어야 한다.
    context: Context = dataclass_field(default_factory=Context)


def analyze(
    netlist_text: str,
    *,
    filename: str = "",
    bom_bytes: bytes | None = None,
    firmware: object | None = None,
    fact_store: FactStore | None = None,
) -> Analysis:
    """넷리스트 본문을 받아 검사까지 끝낸다.

    BOM 은 이제 실제로 파싱한다 — 부품기호와 부품번호를 읽는다.
    firmware 는 아직 파서가 없다. None 이 아니면 '입력은 있다'로만 취급하고,
    그 입력을 NEEDS 로 선언한 규칙은 여전히 미구현이라 건너뛴다.
    있는 척하지 않는다.

    `fact_store` 를 주면 **BOM 의 부품번호로 사실 DB 를 조회**해서 규칙에 넘긴다.
    조회는 여기서 끝난다 — 규칙 함수는 DB 를 모른다 (CLAUDE.md 2-1).
    아는 게 하나도 없으면 `Context.datasheet` 를 None 으로 둔다.
    빈 `FactSet` 을 넘기면 엔진이 "데이터시트가 있다"고 착각한다.
    """
    netlist = parse_text(netlist_text, filename=filename)
    graph = Graph(netlist)

    bom = parse_bom_bytes(bom_bytes) if bom_bytes else None

    lookup = _lookup_facts(fact_store, bom)
    facts: FactSet | None = None
    if lookup is not None and len(lookup.facts) > 0:
        facts = lookup.facts

    ctx = Context(netlist=graph, bom=bom, firmware=firmware, datasheet=facts)
    return Analysis(
        netlist=netlist,
        graph=graph,
        engine=run(ctx),
        bom=bom,
        facts=lookup,
        context=ctx,
    )


def _lookup_facts(store: FactStore | None, bom: Bom | None) -> Lookup | None:
    """BOM 에서 부품번호를 모아 캐시를 한 번만 두드린다."""
    if store is None or bom is None:
        return None
    mpns = bom.mpns
    return store.lookup(mpns) if mpns else None
