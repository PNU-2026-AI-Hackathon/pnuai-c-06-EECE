"""R11 — 네트명이 주장하는 전압과 소스 부품의 전원 도메인이 다름.

회로도만으로 **플래그를 세운다**. 그래서 '기본' 등급이다.

다만 플래그를 **지울 때는** 데이터시트를 본다. 전원이 5V인 부품이라고 출력도 5V인 것은
아니다 — 내부에서 3.3V로 내보내는 부품이 흔하고, 그러면 `PRESENCE_3V3` 이라는 이름이
맞고 이 경고가 오탐이다. 오탐이 최우선 적이다 (CLAUDE.md 2-3).
"""

from __future__ import annotations

from ..netlist.d356 import NET_NAME_WIDTH
from ..netlist.graph import (
    CONFIDENCE_HIGH,
    DOMAIN_EPSILON_V,
    Graph,
    SUPPLY_PIN_PATTERN,
    format_volts,
    names_a_control,
    volts,
    voltage_is_clipped,
)
from ..text import eun
from ..types import Context, Evidence, Finding, Severity, Verdict
from ._clearance import ask_output_bound, number

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

        # **이름이 제어 대상을 말하는 경우는 전압 주장이 아니다.**
        # `24V_ON` 은 3.3V MCU 가 24V 를 켜는 신호다 — 이름의 `24V` 를 반박하면
        # 정상 설계를 결함으로 지목하게 된다. 홀드아웃 보드에서 실제로 그랬다.
        if names_a_control(net):
            continue

        for ref in graph.refs_on(net):
            domain = graph.domain(ref)
            if not domain.known:
                continue
            if abs(domain.volts - claimed) <= DOMAIN_EPSILON_V:
                continue

            source_pin = graph.pin_on_net(ref, net)

            # **이 부품이 여기서 전원을 *받는* 중이면 소스가 아니다.**
            #
            # `U1.VIN → /5V_IN` 을 보고 "이 네트를 구동하는 U1 은 3.3V" 라고 말하고 있었다.
            # 거꾸로다 — U1 이 5V 를 먹고 안에서 3.3V 를 만든다. 부품의 내부 도메인은
            # **자기 전원 입력 네트의 전압에 대해 아무 말도 하지 않는다.**
            if source_pin and SUPPLY_PIN_PATTERN.match(source_pin):
                continue

            # **"이 부품은 어느 레일에 닿아 있더라" 로는 네트 이름을 반박하지 못한다.**
            #
            # 4핀 커넥터 J3 이 2번 핀에서 +5V 에 닿는다는 이유로 도메인이 5V 가 됐고,
            # 그걸 근거로 `24V_ON` 이라는 이름을 "사실은 5V" 라고 반박했다. 커넥터는
            # 핀마다 다른 신호를 나르므로 **부품 하나에 도메인 하나**라는 전제가 안 선다.
            #
            # 자기 전원 핀에서 읽은 도메인(`high`)만 쓴다. 좌표 클러스터로 읽은 것도
            # 여기서는 안 쓴다 — 이 규칙의 주장이 "이 핀의 전압" 이라서다 (헌법 2-2).
            if domain.confidence != CONFIDENCE_HIGH:
                continue
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

            # 이름이 14자 칸에 꽉 찼고 전압 토큰이 그 끝에 걸쳐 있으면 값이 잘렸을 수
            # 있다 — `..._3V` 가 `_3V3` 의 앞부분인 경우다. 그 값으로 FAIL 을 내면
            # 오탐이다. 판정을 내리지 않고 무엇을 확인해야 하는지 적는다 (A++2).
            clipped = voltage_is_clipped(
                net, width_limited=graph.netlist.NAME_IS_WIDTH_LIMITED
            )

            claim = (
                f"네트 이름은 {format_volts(claimed)}V라고 말하는데, "
                f"이 네트를 구동하는 {eun(ref)} {format_volts(domain.volts)}V로 동작합니다."
            )
            if clipped:
                claim += (
                    f" 다만 이 이름은 넷리스트의 {NET_NAME_WIDTH}자 칸을 꽉 채웠고 "
                    "전압 표기가 그 끝에 걸쳐 있어, 원래 이름이 잘렸을 수 있습니다."
                )
            suggestion = (
                "이름을 바꾸든 회로를 바꾸든 하나는 필요합니다. "
                "이름만 맞추면 다음 사람이 또 속습니다."
            )
            evidence = [Evidence.netlist("\n".join(lines), highlight)]
            verdict = Verdict.FAIL
            clipped_reason: str | None = None
            if clipped:
                # 값을 못 믿으면 판정을 내리지 않는다. 무엇을 보면 풀리는지 적는다.
                verdict = Verdict.UNRESOLVED
                clipped_reason = (
                    f"네트명이 {NET_NAME_WIDTH}자에서 잘렸을 수 있어 "
                    f"{format_volts(claimed)}V 라는 표기를 믿을 수 없습니다 — "
                    "EDA 원본에서 이 네트의 전체 이름을 확인해 주세요"
                )

            # --- 전원 전압과 출력 전압은 다르다. 데이터시트가 있으면 그걸로 판정한다
            answer = ask_output_bound(ctx, ref)
            unresolved = clipped_reason or answer.missing
            voh = number(answer)
            if voh is not None:
                cite = answer.evidence()
                if cite is not None:
                    evidence.append(cite)
                unresolved = None

                if clipped:
                    # 데이터시트가 출력 전압을 말해 줘도 **비교 대상인 이름**이 잘렸다.
                    # 무엇과 비교하는지 모르는 채로 해제하면 그게 더 나쁘다.
                    unresolved = clipped_reason
                elif abs(voh - claimed) <= DOMAIN_EPSILON_V:
                    verdict = Verdict.PASS
                    claim = (
                        f"네트 이름 {eun(net)} 맞습니다. {ref}({answer.mpn})의 전원은 "
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

            if unresolved is clipped_reason and clipped_reason is not None:
                verdict = Verdict.UNRESOLVED

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
