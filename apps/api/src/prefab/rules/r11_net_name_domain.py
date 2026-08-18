"""R11 — 네트명이 주장하는 전압과 소스 부품의 전원 도메인이 다름.

회로도만으로 **플래그를 세운다**. 그래서 '기본' 등급이다.

다만 플래그를 **지울 때는** 데이터시트를 본다. 전원이 5V인 부품이라고 출력도 5V인 것은
아니다 — 내부에서 3.3V로 내보내는 부품이 흔하고, 그러면 `PRESENCE_3V3` 이라는 이름이
맞고 이 경고가 오탐이다. 오탐이 최우선 적이다 (CLAUDE.md 2-3).
"""

from __future__ import annotations

from ..datasheet.facts import VOH_MAX
from ..netlist.graph import DOMAIN_EPSILON_V, Graph, format_volts, volts
from ..types import Context, Evidence, Finding, Severity, Verdict
from ._clearance import ask, number

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

            claim = (
                f"네트 이름은 {format_volts(claimed)}V라고 말하는데, "
                f"이 네트를 구동하는 {ref}는 {format_volts(domain.volts)}V로 동작합니다."
            )
            suggestion = (
                "이름을 바꾸든 회로를 바꾸든 하나는 필요합니다. "
                "이름만 맞추면 다음 사람이 또 속습니다."
            )
            evidence = [Evidence.netlist("\n".join(lines), highlight)]
            verdict = Verdict.FAIL

            # --- 전원 전압과 출력 전압은 다르다. 데이터시트가 있으면 그걸로 판정한다
            answer = ask(ctx, ref, VOH_MAX)
            unresolved = answer.missing
            voh = number(answer)
            if voh is not None:
                cite = answer.evidence()
                if cite is not None:
                    evidence.append(cite)
                unresolved = None

                if abs(voh - claimed) <= DOMAIN_EPSILON_V:
                    verdict = Verdict.PASS
                    claim = (
                        f"네트 이름 {net} 은 맞습니다. {ref}({answer.mpn})의 전원은 "
                        f"{format_volts(domain.volts)}V지만 출력은 {format_volts(voh)}V입니다."
                    )
                    suggestion = (
                        f"조치할 것이 없습니다. 데이터시트에서 확인했습니다 — {answer.fact.cite()}."
                    )
                else:
                    claim = (
                        f"{claim} 출력 전압도 {format_volts(voh)}V로 확인되어 "
                        f"이름과 맞지 않습니다."
                    )
                    suggestion = f"{suggestion} 데이터시트 근거 — {answer.fact.cite()}."

            findings.append(
                Finding(
                    rule=RULE_ID,
                    title=TITLE,
                    tier=TIER,
                    severity=SEVERITY,
                    verdict=verdict,
                    net=net,
                    claim=claim,
                    evidence=tuple(evidence),
                    suggestion=suggestion,
                    unresolved_reason=unresolved,
                )
            )

    return findings
