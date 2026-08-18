"""R12 — 상위 전원 도메인이 하위를 직결.

높은 전원으로 도는 부품과 낮은 전원으로 도는 부품이 같은 네트에
직렬 저항·분압·레벨 시프터 없이 물려 있는 경우를 찾는다.

토폴로지가 질문을 던진다. 데이터시트가 답한다 —
구동부의 Voh 가 VOH_SAFE_MAX_V 이하로 확인되면 이 발견은 **해제된다**.
사실을 못 찾으면 추측하지 않고, **무엇이 있으면 풀리는지**를 적어 미결로 둔다.
비교는 여전히 결정적 코드가 한다. 데이터시트는 값을 줄 뿐이다 (CLAUDE.md 2-1).

**단정하지 않는 두 가지** (요청서 A-1 · A-2)
- 누가 누구를 구동하는지: 핀 이름이 출력이라고 말할 때만 쓴다. `pad-` 는 모른다.
- 네트에 붙은 저항의 정체: 반대쪽 터미널을 보고 풀업/풀다운/분기를 가른다.
"""

from __future__ import annotations

from ..netlist.graph import (
    CONFIDENCE_HIGH,
    DOMAIN_EPSILON_V,
    Graph,
    format_volts,
)
from ..datasheet.facts import VOH_MAX
from ..text import eun, gwa, i_ga
from ..types import Context, Evidence, Finding, Severity, Verdict
from ._clearance import Answer, ask, number

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

        # 도메인을 추론으로만 안다면 그 부품이 **구동하는 쪽인지도 모른다.**
        # 넷리스트에는 핀 방향이 없다. Voh 는 구동하는 쪽에나 물어볼 값이라,
        # 방향을 모르면 Voh 를 알아도 그걸로 해제하면 안 된다 (CLAUDE.md 2-2).
        sure = graph.domain(hi).confidence == CONFIDENCE_HIGH
        answer = ask(
            ctx, hi, VOH_MAX,
            resolve=sure,
            what=None if sure else "핀 방향과 내부 풀업",
        )
        findings.append(_finding(graph, net, hi, lo, hi_v, lo_v, answer))

    return findings


def _finding(graph: Graph, net, hi, lo, hi_v, lo_v, answer: Answer) -> Finding:
    hi_conf = graph.domain(hi).confidence
    hi_token = graph.ref_pin(hi, net)
    lo_token = graph.ref_pin(lo, net)
    hi_supply = graph.supply_pin_of(hi)
    lo_supply = graph.supply_pin_of(lo)

    passives = [(ref, graph.passive_role(ref, net)) for ref in graph.series_candidates(net)]

    # ---------------------------------------------------------------- claim
    hi_desc = f"{format_volts(hi_v)}V로 " + ("동작하는" if hi_conf == CONFIDENCE_HIGH else "추정되는")
    if graph.drives(hi, net):
        head = (
            f"{hi_desc} {hi}의 출력({hi_token})이 "
            f"{format_volts(lo_v)}V로 동작하는 {lo_token}에 직결되어 있습니다."
        )
    else:
        # 어느 쪽이 구동하는지는 넷리스트만으로 알 수 없다. 단정하지 않는다.
        head = (
            f"{hi_desc} {gwa(hi)} {format_volts(lo_v)}V로 동작하는 {i_ga(lo)} "
            f"같은 네트에 직결되어 있습니다 ({hi_token} · {lo_token})."
        )

    if passives:
        parts = ", ".join(f"{eun(ref)} {role.phrase}" for ref, role in passives)
        tail = f"이 네트의 {parts}이라 직렬 보호가 되지 않습니다."
    else:
        tail = "사이에 직렬 저항도 분압도 레벨 시프터도 없습니다."

    # ------------------------------------------------------------- evidence
    lines: list[str] = []
    shown_rails: set[str] = set()

    if hi_supply:
        pin, rail = hi_supply
        lines.append(f"{hi}.{pin} → {rail}")
        shown_rails.add(rail)
    lines.append(f"{hi_token} → {net}")

    passive_marks: list[str] = []
    for ref, role in passives:
        lines.append(f"{ref}.{graph.pin_on_net(ref, net)} → {net}")
        if role.other_net:
            lines.append(f"{ref} 반대쪽 → {role.other_net}   ({role.role})")
            shown_rails.add(role.other_net)
            passive_marks.append(role.other_net)

    lines.append(f"{lo_token} → {net}")
    if lo_supply and lo_supply[1] not in shown_rails:
        lines.append(f"{lo}.{lo_supply[0]} → {lo_supply[1]}")

    if hi_supply:
        highlight = [hi_supply[1], hi_token, lo_token]
    else:
        highlight = [hi_token, *passive_marks, lo_token]

    # ----------------------------------------------------------- suggestion
    if passives:
        roles = " · ".join(sorted({role.role for _ref, role in passives}))
        suggestion = (
            f"{hi}의 부품번호를 제출하면 출력 규격으로 판정합니다. "
            f"이 네트의 저항은 {roles}이라 직렬로 옮기지 않는 한 보호가 되지 않습니다."
        )
    else:
        suggestion = (
            f"{hi}의 부품번호(MPN)를 BOM으로 제출하면 데이터시트의 출력 하이 전압(Voh)을 "
            f"읽어 판정합니다. Voh가 {format_volts(VOH_SAFE_MAX_V)}V 이하면 이 항목은 해제됩니다."
        )

    evidence: list[Evidence] = [Evidence.netlist("\n".join(lines), highlight)]
    claim = f"{head} {tail}"
    verdict = Verdict.FAIL
    unresolved: str | None = answer.missing

    # 방향을 모르면 미결 사유가 그 사실부터 말한다. 부품번호만 문제인 게 아니다
    if hi_conf != CONFIDENCE_HIGH and unresolved is not None:
        unresolved = (
            f"{hi}이 이 네트를 구동하는지 입력으로 받는지 넷리스트만으로는 알 수 없습니다. "
            f"{unresolved}"
        )

    # ------------------------------------------------- 데이터시트가 답한 경우
    voh = number(answer)
    if voh is not None:
        cite = answer.evidence()
        if cite is not None:
            evidence.append(cite)
        unresolved = None

        if voh <= VOH_SAFE_MAX_V:
            verdict = Verdict.PASS
            claim = (
                f"{head} 다만 {hi}({answer.mpn})의 출력 하이 전압은 "
                f"{format_volts(voh)}V로 확인되어 {lo}의 {format_volts(lo_v)}V 입력이 견딥니다. "
                f"전원이 {format_volts(hi_v)}V일 뿐 출력은 그렇지 않습니다."
            )
            suggestion = (
                f"조치할 것이 없습니다. 데이터시트에서 확인했습니다 — {answer.fact.cite()}. "
                f"{hi}의 부품번호가 바뀌면 이 판정도 다시 해야 합니다."
            )
        else:
            claim = (
                f"{head} {tail} {hi}({answer.mpn})의 출력 하이 전압이 "
                f"{format_volts(voh)}V로 확인되어 {format_volts(VOH_SAFE_MAX_V)}V 한도를 넘습니다."
            )
            suggestion = (
                f"레벨 시프터나 분압이 필요합니다. 추정이 아니라 데이터시트 값입니다 — "
                f"{answer.fact.cite()}."
            )

    return Finding(
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
