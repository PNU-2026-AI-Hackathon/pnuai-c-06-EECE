"""R11 — 네트명이 주장하는 전압과 소스 부품의 전원 도메인이 다름.

회로도만으로 판정한다. 데이터시트를 한 번도 읽지 않는다. 그래서 '기본' 등급이다.
"""

from __future__ import annotations

from ..netlist.graph import DOMAIN_EPSILON_V, Graph, format_volts, volts
from ..types import Context, Evidence, Finding, Severity, Verdict

RULE_ID = "R11"
TITLE = "네트명이 주장하는 전압과 소스 부품의 전원 도메인이 다름"
SEVERITY = Severity.WARNING
TIER = "기본"
NEEDS = ["netlist"]


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    graph: Graph = ctx.netlist
    findings: list[Finding] = []

    for net in graph.signal_nets():
        claimed = volts(net)
        if claimed is None:
            continue

        for ref in graph.refs_on(net):
            domain = graph.domain(ref)
            if not domain.known:
                continue
            if abs(domain.volts - claimed) <= DOMAIN_EPSILON_V:
                continue

            source_pin = graph.pin_on_net(ref, net)
            lines = [f"네트명: {net}"]
            highlight = [net]

            supply = graph.supply_pin_of(ref)
            if supply:
                supply_pin, rail = supply
                lines.append(f"{ref}.{supply_pin} → {rail}   ({ref} 전원 도메인 = {domain.volts}V)")
                highlight.append(rail)
            else:
                lines.append(f"{domain.basis}   ({ref} 전원 도메인 = {domain.volts}V)")

            if source_pin is not None:
                lines.append(f"{ref}.{source_pin} → {net}   (이 네트의 소스)")

            findings.append(
                Finding(
                    rule=RULE_ID,
                    title=TITLE,
                    tier=TIER,
                    severity=SEVERITY,
                    verdict=Verdict.FAIL,
                    net=net,
                    claim=(
                        f"네트 이름은 {format_volts(claimed)}V라고 말하는데, "
                        f"이 네트를 구동하는 {ref}는 {format_volts(domain.volts)}V로 동작합니다."
                    ),
                    evidence=(Evidence.netlist("\n".join(lines), highlight),),
                    suggestion=(
                        "이름을 바꾸든 회로를 바꾸든 하나는 필요합니다. "
                        "이름만 맞추면 다음 사람이 또 속습니다."
                    ),
                    unresolved_reason=f"{ref} 미식별 — BOM 필요",
                )
            )

    return findings
