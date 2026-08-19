"""R04 — 외부 부품 출력이 GPIO 입력 최대 정격 초과.

R12 와 묻는 것이 다르다.

```
R12   전원 도메인이 다른가?          넷리스트 토폴로지로 본다
R04   출력 전압이 절대 최대를 넘나?   양쪽 데이터시트 숫자로 본다
```

그래서 R04 는 **양쪽 부품의 데이터시트가 다 있어야** 말을 한다.
하나라도 없으면 조용히 있는다 — 그 자리는 R12 가 이미 미결로 말하고 있고,
여기서 또 말하면 같은 네트에 경고가 두 번 쌓인다 (CLAUDE.md 2-3 오탐이 최우선 적).

**핀 방향을 몰라도 판정할 수 있다.** A 가 5V 를 낼 수 있고 B 가 3.6V 까지만
견딘다면, 누가 구동하든 그 둘을 직결한 것 자체가 위험하다.
"""

from __future__ import annotations

from ..datasheet.facts import VIN_ABSOLUTE_MAX, label
from ..netlist.graph import Graph, format_volts
from ..types import Context, Evidence, Finding, Severity, Verdict
from ._clearance import ask, ask_output_bound, number

RULE_ID = "R04"
TITLE = "외부 부품 출력이 GPIO 입력 최대 정격 초과"
SEVERITY = Severity.CRITICAL
TIER = "기본"
NEEDS = ["netlist", "bom"]


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    graph: Graph = ctx.netlist
    findings: list[Finding] = []

    for net in graph.signal_nets():
        refs = graph.refs_on(net)
        # 낼 수 있는 전압을 아는 부품과, 견디는 한계를 아는 부품을 각각 모은다.
        outputs = {}
        limits = {}
        for ref in refs:
            out = ask_output_bound(ctx, ref)
            if out.answered and number(out) is not None:
                outputs[ref] = out
            lim = ask(ctx, ref, VIN_ABSOLUTE_MAX)
            if lim.answered and number(lim) is not None:
                limits[ref] = lim

        for source, out in outputs.items():
            for sink, lim in limits.items():
                if source == sink:
                    continue
                volts, ceiling = number(out), number(lim)
                if volts <= ceiling:
                    continue
                findings.append(_finding(graph, net, source, sink, out, lim, volts, ceiling))

    return findings


def _finding(graph, net, source, sink, out, lim, volts, ceiling) -> Finding:
    source_pin = graph.pin_on_net(source, net)
    sink_pin = graph.pin_on_net(sink, net)
    what = label(out.fact.field)

    lines = [f"{source}.{source_pin} → {net}", f"{sink}.{sink_pin} → {net}"]
    evidence = [
        Evidence.netlist("\n".join(lines), [f"{source}.{source_pin}", f"{sink}.{sink_pin}"]),
    ]
    for answer in (out, lim):
        cite = answer.evidence()
        if cite is not None:
            evidence.append(cite)

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.FAIL,
        net=net,
        claim=(
            f"{source}({out.mpn})의 {what}은 {format_volts(volts)}V인데, "
            f"같은 네트에 물린 {sink}({lim.mpn})가 견디는 절대 최대 입력은 "
            f"{format_volts(ceiling)}V입니다. {format_volts(volts - ceiling)}V 초과입니다."
        ),
        evidence=tuple(evidence),
        suggestion=(
            f"레벨 시프터나 분압으로 {format_volts(ceiling)}V 이하로 낮추세요. "
            f"절대 최대 정격을 넘으면 {sink}가 파손됩니다 — 동작 이상이 아니라 고장입니다. "
            f"추정이 아니라 양쪽 데이터시트 값입니다 ({out.fact.cite()} · {lim.fact.cite()})."
        ),
        unresolved_reason=None,
    )
