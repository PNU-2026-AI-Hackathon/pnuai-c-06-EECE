"""R08 — 회로도에 연결됐는데 코드가 초기화 안 함.

R07 의 반대 방향이다. 회로도가 먼저 바뀌고 코드가 안 따라온 자리를 잡는다.
배선은 있는데 코드가 그 핀을 한 번도 만지지 않으면, 그 부품은 그냥 안 움직인다.

경고 등급이다 — 의도적으로 남겨둔 미래용 배선일 수 있다.
그래서 "고장"이 아니라 "확인 필요"로 낸다 (오탐이 최우선 적, CLAUDE.md 2-3).

**부재도 근거다.** 이 판정에는 가리킬 줄이 없다. 그래서 firmware 근거의 `line` 을
`null` 로 두고, 무엇을 다 읽었고 무엇이 없었는지를 `snippet` 에 적는다.
`line: 1` 같은 값을 지어내지 않는다 — 사용자가 그 줄을 열어본다 (계약 「부재도 근거다」).
"""

from __future__ import annotations

from ..netlist.d356 import Netlist
from ..text import eul, eun
from ..types import Context, Evidence, Finding, Severity, Verdict

RULE_ID = "R08"
TITLE = "회로도에 연결됐는데 코드가 초기화 안 함"
SEVERITY = Severity.WARNING
TIER = "차별"
NEEDS = ["netlist", "firmware"]


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO 금지."""
    graph = ctx.netlist
    firmware = ctx.firmware
    netlist: Netlist = graph.netlist
    pinmap = graph.pinmap

    # 전원·접지 레일은 신호가 아니다. 코드가 만질 대상이 아니므로 대상에서 뺀다.
    signal_nets = set(graph.signal_nets())

    findings: list[Finding] = []

    for pad in pinmap.gpio_pads():
        net = netlist.net_at(pad.ref, pad.pin, pad.x, pad.y)
        if netlist.is_dangling(net):
            continue  # 배선이 없으면 이 규칙의 대상이 아니다 (R07 이 본다)
        if net not in signal_nets:
            continue  # 전원·접지에 물린 핀은 코드가 만질 것이 아니다

        if firmware.find(silk=pad.silk, gpio=pad.gpio) is not None:
            continue  # 코드가 이미 쓴다

        findings.append(_finding(graph, pad, net, netlist, firmware))

    return findings


def _netlist_lines(graph, pad, net: str, netlist: Netlist) -> list[str]:
    """이 네트에 무엇이 붙어 있는지. 저항은 반대쪽까지 밝힌다."""
    rows: list[tuple[str, str]] = [(f"{pad.ref}.{pad.silk} ({_gpio(pad)}, 패드명 {pad.pin})", net)]
    notes: dict[str, str] = {}

    for ref, pin in netlist.connections(net):
        if ref == pad.ref:
            continue
        rows.append((f"{ref}.{pin}", net))
        role = graph.passive_role(ref, net) if ref in graph.series_candidates(net) else None
        if role is not None and role.other_net:
            notes[f"{ref}.{pin}"] = f"{ref} 반대쪽 → {role.other_net}, {role.role}"

    width = max(len(left) for left, _ in rows)
    return [
        f"{left.ljust(width)} → {right}" + (f"   ({notes[left]})" if left in notes else "")
        for left, right in rows
    ]


def _gpio(pad) -> str:
    return f"GPIO{pad.gpio}" if pad.gpio is not None else "GPIO 미상"


def _finding(graph, pad, net: str, netlist: Netlist, firmware) -> Finding:
    labels = " · ".join(firmware.labels) or "없음"

    evidence = [
        Evidence.netlist(
            "\n".join(_netlist_lines(graph, pad, net, netlist)),
            [f"{pad.ref}.{pad.silk}", net],
        ),
        Evidence.firmware(
            file=firmware.files[0] if firmware.files else "(소스 없음)",
            line=None,  # 가리킬 줄이 없다. 부재가 근거다.
            snippet=(
                f"검사한 파일 {len(firmware.files)}개 · {firmware.total_lines}줄 · "
                f"참조한 핀 {len(firmware.pins)}개 ({labels})\n"
                f"{eun(pad.silk)} 어느 파일에도 나오지 않습니다."
            ),
            highlight=[pad.silk],
        ),
    ]

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.FAIL,
        net=net,
        claim=(
            f"회로도는 {pad.silk}({_gpio(pad)})"
            f"{'을' if eul(pad.silk).endswith('을') else '를'} {net} 로 배선해 뒀는데, "
            f"코드에는 이 핀이 한 번도 나오지 않습니다."
        ),
        evidence=tuple(evidence),
        suggestion=(
            f"코드에서 {eul(pad.silk)} 초기화하고 제어하세요. "
            "초기화하지 않으면 부팅 후 핀이 뜬 상태로 남아 연결된 부품이 임의로 동작할 수 있습니다. "
            "아직 쓸 계획이 없는 미래용 배선이라면 그대로 두셔도 됩니다."
        ),
        # 배선이 있고 코드에 없다는 것은 양쪽 다 확인된 사실이다. 보류하지 않는다.
        unresolved_reason=None,
    )
