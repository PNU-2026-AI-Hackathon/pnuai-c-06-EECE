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
    ROLE_PULLUP,
    format_volts,
    volts,
)
from ..datasheet.facts import INPUT_PULLUP_TO, NO_PULLUP, OPEN_DRAIN, OUTPUT_TYPE, label
from ..text import eul, eun, gwa, i_ga
from ..types import Context, Evidence, Finding, Severity, Verdict
from ._clearance import Answer, ask, ask_output_bound, number

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

        # 방향을 모를 때는 Voh 를 물어봐야 소용이 없다. 대신 **다른 질문**이 남는다 —
        # "그 핀에서 상위 레일로 가는 길이 있는가". 내부 풀업이 없으면 그 부품은
        # 이 네트에 자기 레일을 올릴 수 없다. 측정 한 번으로 답이 나오는 질문이다.
        pullup = ask(ctx, hi, INPUT_PULLUP_TO, what="입력 핀의 내부 풀업")
        if not sure and _no_path_up(pullup):
            findings.append(_cleared_by_pullup(graph, net, hi, lo, hi_v, lo_v, pullup))
            continue

        bounded_to = _pullup_bound(graph, net, lo_v)

        # **오픈드레인 + 낮은 쪽 레일 풀업 = 올라올 길이 없다.**
        #
        # 오픈드레인 출력은 로우로 끌어내리기만 하고, 하이일 때는 고임피던스다.
        # 그러면 이 네트의 하이 레벨을 정하는 것은 상위 부품이 아니라 **풀업**이고,
        # 풀업이 3.3V 로 가면 3.3V 를 넘지 않는다.
        #
        # 풀업 하나만으로는 이걸 못 말한다 — 푸시풀이면 풀업과 무관하게 5V 를 낸다.
        # 그래서 팀이 "풀업이 있다고 안전해지지 않는다" 로 정했었다. **데이터시트가
        # 오픈드레인이라고 말해 주면 그때 나머지 절반이 채워진다.**
        #
        # 실측에서 나온 자리다: TP4056 의 `~CHRG`·`~STDBY` 가 +3.3V 로 풀업된 채
        # 3.3V MCU 와 만나 치명 2건으로 떴는데, 데이터시트 2쪽이
        # "Open Drain Charge Status Output ... otherwise pin is in high impedance state"
        # 라고 적고 있었다.
        drive = ask(ctx, hi, OUTPUT_TYPE, what="출력 방식")
        if bounded_to and _is_open_drain(drive):
            findings.append(
                _cleared_by_open_drain(graph, net, hi, lo, hi_v, lo_v, drive, bounded_to)
            )
            continue

        answer = ask_output_bound(
            ctx, hi,
            resolve=sure,
            what=None if sure else "핀 방향과 내부 풀업",
        )
        findings.append(
            _finding(graph, net, hi, lo, hi_v, lo_v, answer, bounded_to=bounded_to)
        )

    return findings


def _pullup_bound(graph: Graph, net: str, lo_v: float) -> str | None:
    """이 네트를 **낮은 쪽 레일로 끌어올리는 풀업**이 있으면 그 레일 이름.

    있으면 이야기가 달라진다. 오픈드레인 출력에 3.3V 풀업을 다는 것은 5V 부품을
    3.3V 로직에 붙이는 **표준 관용구**다 — 풀업이 하이 레벨을 3.3V 로 정하고,
    상위 부품은 로우로 끌어내리기만 한다. 그러면 5V 가 올라올 일이 없다.

    **증명은 아니다.** 그 핀이 푸시풀이면 풀업과 무관하게 5V 를 낸다. 다만 그때는
    풀업을 달 이유가 없다 — 드라이버와 싸우기만 한다. 그래서 이건 설계자가
    "이 네트는 3.3V 레벨" 이라고 말한 흔적이고, **치명이라 단정할 근거는 못 된다.**

    남의 실제 보드에서 충전 IC 의 `~CHRG`·`~STDBY` 가 정확히 이 모양이었다.
    """
    for ref in graph.series_candidates(net):
        role = graph.passive_role(ref, net)
        if role.role != ROLE_PULLUP or not role.other_net:
            continue
        rail = volts(role.other_net)
        if rail is not None and rail <= lo_v + DOMAIN_EPSILON_V:
            return role.other_net
    return None


def _is_open_drain(answer: Answer) -> bool:
    """확인 결과 **오픈드레인이라고 나왔는가.** 모르면 False.

    `value` 는 `facts.normalize_output_type` 이 상수로 옮겨 둔 것이다 —
    데이터시트는 문장으로 적고(`Open Drain Charge Status Output`) 규칙은 상수를 본다.
    """
    f = answer.fact
    return f is not None and f.usable and f.value == OPEN_DRAIN


def _cleared_by_open_drain(
    graph: Graph, net, hi, lo, hi_v, lo_v, answer: Answer, bounded_to: str
) -> Finding:
    """오픈드레인이라 하이 레벨을 풀업이 정하는 경우. 발견을 해제한다."""
    hi_token = graph.ref_pin(hi, net)
    lo_token = graph.ref_pin(lo, net)

    evidence = [
        Evidence.netlist(
            f"{hi_token} → {net}\n{lo_token} → {net}\n{net} → {bounded_to} (풀업)",
            [hi_token, lo_token, bounded_to],
        )
    ]
    cite = answer.evidence()
    if cite is not None:
        evidence.append(cite)

    return Finding(
        rule=RULE_ID, title=TITLE, tier=TIER, severity=SEVERITY,
        verdict=Verdict.PASS, net=net,
        claim=(
            f"{format_volts(hi_v)}V 로 도는 {gwa(hi)} {format_volts(lo_v)}V 로 도는 "
            f"{i_ga(lo)} 같은 네트에 있습니다. 다만 {hi}({answer.mpn}) 의 이 핀이 "
            f"오픈드레인으로 확인돼, 하이 레벨은 {i_ga(hi)} 아니라 {bounded_to} 풀업이 "
            f"정합니다 — {format_volts(lo_v)}V 를 넘지 않습니다."
        ),
        evidence=tuple(evidence),
        suggestion=(
            f"조치할 것이 없습니다. 다만 {bounded_to} 풀업이 사라지면 이 핀은 뜨게 되므로 "
            f"그 저항을 빼지 마세요. {hi} 의 부품번호가 바뀌면 이 판정도 다시 해야 합니다."
        ),
        unresolved_reason=None,
    )


def _no_path_up(answer: Answer) -> bool:
    """확인 결과 내부 풀업이 **없다**고 나왔는가.

    `value is None` 은 "모른다" 다. 여기서 필요한 건 "없다" 이고 그건 `NO_PULLUP` 이다.
    둘을 섞으면 모르는 것을 안다고 말하게 된다.
    """
    f = answer.fact
    return f is not None and f.usable and f.value == NO_PULLUP


def _cleared_by_pullup(graph: Graph, net, hi, lo, hi_v, lo_v, answer: Answer) -> Finding:
    """상위 레일로 가는 길이 없다는 것이 확인된 경우. 발견을 해제한다."""
    hi_token = graph.ref_pin(hi, net)
    lo_token = graph.ref_pin(lo, net)
    f = answer.fact

    evidence = [
        Evidence.netlist(
            f"{hi_token} → {net}\n{lo_token} → {net}",
            [hi_token, lo_token],
        )
    ]
    cite = answer.evidence()
    if cite is not None:
        evidence.append(cite)

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.PASS,
        net=net,
        claim=(
            f"{format_volts(hi_v)}V 로 도는 {gwa(hi)} {format_volts(lo_v)}V 로 도는 {i_ga(lo)} "
            f"같은 네트에 있습니다. 다만 {hi}({answer.mpn}) 의 입력 핀에는 내부 풀업이 "
            f"없는 것으로 확인돼, 이 핀을 통해 {format_volts(hi_v)}V 가 {lo} 로 올라올 "
            f"경로가 없습니다."
        ),
        evidence=tuple(evidence),
        suggestion=(
            f"조치할 것이 없습니다. 근거 — {f.cite() if f else '출처 없음'}. "
            f"다만 저항계는 트랜지스터·다이오드 경로를 못 봅니다. "
            f"{answer.mpn} 의 회로도나 모듈 모델명을 알면 완전히 닫힙니다."
        ),
        unresolved_reason=None,
    )


def _finding(
    graph: Graph, net, hi, lo, hi_v, lo_v, answer: Answer, *, bounded_to: str | None = None
) -> Finding:
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
    # **이미 낸 것을 또 내라고 하지 않는다.** 부품번호를 아는데 "부품번호를 제출하면"
    # 이라고 쓰면, 사용자는 자기가 뭘 빠뜨렸는지 찾다가 시간을 버린다.
    if answer.mpn:
        need = f"{hi}({answer.mpn})의 데이터시트를 읽으면 판정합니다."
    else:
        need = (
            f"{hi}의 부품번호(MPN)를 BOM으로 제출하면 데이터시트의 출력 하이 전압(Voh)을 "
            f"읽어 판정합니다."
        )

    if passives:
        roles = " · ".join(sorted({role.role for _ref, role in passives}))
        suggestion = (
            f"{need} 이 네트의 저항은 {roles}이라 직렬로 옮기지 않는 한 보호가 되지 않습니다."
        )
    else:
        suggestion = (
            f"{need} Voh가 {format_volts(VOH_SAFE_MAX_V)}V 이하면 이 항목은 해제됩니다."
        )

    # **물어볼 곳을 하나 더 알려준다.** 판정은 그대로 두되, 낮은 쪽 레일로 끌어올리는
    # 풀업이 있으면 그건 오픈드레인 관용구의 흔적이다. 사용자가 데이터시트에서
    # 확인할 항목을 정확히 짚어 주면 한 번 보고 끝난다.
    #
    # **판정을 바꾸지는 않는다.** 풀업이 있어도 푸시풀이면 5V 가 그대로 올라온다.
    # 그 구분은 팀이 이미 정했다 (`test_pullup_is_not_counted_as_series_protection`).
    if bounded_to:
        suggestion += (
            f" {i_ga(hi_token)} 오픈드레인이면 하이 레벨을 풀업이 정하므로 "
            f"{eul(bounded_to)} 넘지 않습니다 — 데이터시트에서 그 핀의 출력 방식을 확인하세요."
        )

    evidence: list[Evidence] = [Evidence.netlist("\n".join(lines), highlight)]
    claim = f"{head} {tail}"
    verdict = Verdict.FAIL
    unresolved: str | None = answer.missing

    # 방향을 모르면 미결 사유가 그 사실부터 말한다. 부품번호만 문제인 게 아니다
    if hi_conf != CONFIDENCE_HIGH and unresolved is not None:
        unresolved = (
            f"{i_ga(hi)} 이 네트를 구동하는지 입력으로 받는지 넷리스트만으로는 알 수 없습니다. "
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
                f"{head} 다만 {hi}({answer.mpn})의 {i_ga(label(answer.fact.field))} "
                f"{format_volts(voh)}V로 확인되어 {lo}의 {format_volts(lo_v)}V 입력이 견딥니다. "
                f"전원이 {format_volts(hi_v)}V일 뿐 출력은 그렇지 않습니다."
            )
            suggestion = (
                f"조치할 것이 없습니다. 데이터시트에서 확인했습니다 — {answer.fact.cite()}. "
                f"{hi}의 부품번호가 바뀌면 이 판정도 다시 해야 합니다."
            )
        else:
            claim = (
                f"{head} {tail} {hi}({answer.mpn})의 {i_ga(label(answer.fact.field))} "
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
