"""R12 — 상위 전원 도메인이 하위를 직결.

높은 전원으로 도는 부품의 출력이 낮은 전원으로 도는 부품 핀에
직렬 저항·분압·레벨 시프터 없이 바로 물려 있는 경우를 찾는다.

토폴로지가 질문을 던진다. 데이터시트가 답한다 —
구동부의 Voh 가 VOH_SAFE_MAX_V 이하로 확인되면 이 발견은 해제된다.
그 확인은 BOM 이 들어온 뒤에 한다. 지금은 추측하지 않고 unresolved_reason 을 남긴다.
"""

from __future__ import annotations

from ..netlist.graph import (
    CONFIDENCE_HIGH,
    DOMAIN_EPSILON_V,
    Graph,
    format_volts,
)
from ..types import Context, Evidence, Finding, Severity, Verdict

RULE_ID = "R12"
TITLE = "상위 전원 도메인이 하위를 직결"
SEVERITY = Severity.CRITICAL
TIER = "기본"
NEEDS = ["netlist"]

#: 3.3V 입력이 견디는 출력 하이 전압 상한 (V). 이 값 이하로 확인되면 발견이 해제된다.
VOH_SAFE_MAX_V = 3.6

#: 도메인을 아는 능동 부품이 이 수보다 적으면 비교할 대상이 없다.
MIN_ACTIVE_PARTS = 2


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    graph: Graph = ctx.netlist
    findings: list[Finding] = []

    for net in graph.signal_nets():
        actives = graph.active_refs(net)
        if len(actives) < MIN_ACTIVE_PARTS:
            continue

        hi = max(actives, key=lambda r: graph.domain(r).volts)
        lo = min(actives, key=lambda r: graph.domain(r).volts)
        hi_v = graph.domain(hi).volts
        lo_v = graph.domain(lo).volts
        if hi_v - lo_v <= DOMAIN_EPSILON_V:
            continue

        series = graph.series_candidates(net)
        findings.append(_finding(graph, net, hi, lo, hi_v, lo_v, series))

    return findings


def _finding(graph: Graph, net, hi, lo, hi_v, lo_v, series) -> Finding:
    hi_conf = graph.domain(hi).confidence
    hi_pin = graph.pin_on_net(hi, net)
    lo_pin = graph.pin_on_net(lo, net)
    hi_supply = graph.supply_pin_of(hi)
    lo_supply = graph.supply_pin_of(lo)

    # ---------------------------------------------------------------- claim
    if hi_conf == CONFIDENCE_HIGH:
        head = (
            f"{format_volts(hi_v)}V로 동작하는 {hi}의 출력이 "
            f"{format_volts(lo_v)}V로 동작하는 {lo} 핀에 직결되어 있습니다."
        )
    else:
        head = (
            f"{format_volts(hi_v)}V로 추정되는 {hi}이 "
            f"{format_volts(lo_v)}V로 동작하는 {lo}을 직접 구동합니다."
        )

    if series:
        tail = f"이 네트의 {', '.join(series)}는 풀업이라 직렬 보호 역할을 하지 못합니다."
    else:
        tail = "사이에 직렬 저항도 분압도 레벨 시프터도 없습니다."

    # ------------------------------------------------------------- evidence
    lines: list[str] = []
    shown_rails: set[str] = set()

    if hi_supply:
        pin, rail = hi_supply
        lines.append(f"{hi}.{pin} → {rail}")
        shown_rails.add(rail)
    if hi_pin is not None:
        lines.append(f"{hi}.{hi_pin} → {net}")

    passive_marks: list[str] = []
    for ref in series:
        for pin, nets in graph.pins_of(ref).items():
            for n in sorted(nets):
                lines.append(f"{ref}.{pin} → {n}")
                shown_rails.add(n)
                if n != net:
                    passive_marks.append(f"{ref}.{pin}")

    if lo_pin is not None:
        lines.append(f"{lo}.{lo_pin} → {net}")
    if lo_supply and lo_supply[1] not in shown_rails:
        # 이미 화면에 나온 레일을 두 번 적지 않는다
        lines.append(f"{lo}.{lo_supply[0]} → {lo_supply[1]}")

    if hi_supply:
        highlight = [hi_supply[1], f"{hi}.{hi_pin}", f"{lo}.{lo_pin}"]
    else:
        highlight = [f"{hi}.{hi_pin}", *passive_marks, f"{lo}.{lo_pin}"]

    # ----------------------------------------------------------- suggestion
    if series:
        suggestion = (
            f"{hi}의 부품번호를 제출하면 접점/입력 전압 규격으로 판정합니다. "
            f"{', '.join(series)}를 직렬로 옮기는 것만으로는 해결되지 않을 수 있습니다."
        )
    else:
        suggestion = (
            f"{hi}의 부품번호(MPN)를 BOM으로 제출하면 데이터시트의 출력 하이 전압(Voh)을 "
            f"읽어 판정합니다. Voh가 {format_volts(VOH_SAFE_MAX_V)}V 이하면 이 항목은 해제됩니다."
        )

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.FAIL,
        net=net,
        claim=f"{head} {tail}",
        evidence=(Evidence.netlist("\n".join(lines), highlight),),
        suggestion=suggestion,
        unresolved_reason=f"{hi} 미식별 — BOM 필요",
    )
