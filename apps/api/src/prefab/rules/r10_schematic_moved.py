"""R10 — 회로도가 바뀐 뒤 코드가 안 따라옴 (드리프트).

**이 제품의 이름이 붙은 규칙이다.** R07 은 "코드가 쓰는 핀이 안 붙어 있다"고,
R08 은 "붙었는데 코드가 안 쓴다"고 각자 절반씩 말한다. 한 번의 이동이 두 발견으로
쪼개져 나오면 사용자는 **문제가 둘이라고 읽는다.** R10 은 그 둘을 하나로 잇는다.

```
이전   PRESENCE_3V3 → U1.D2      코드: pinMode(D2, ...)
지금   PRESENCE_3V3 → U1.D4      코드: 그대로 D2
       ↑ 회로도가 옮겼고 코드는 안 따라왔다
```

## 왜 이전 넷리스트가 필요한가

지금 한 장만 보면 "D2 가 안 붙었다"와 "D4 를 코드가 안 쓴다"까지가 전부다.
**둘이 같은 사건인지는 이전 상태를 알아야 말할 수 있다.** 모르면 잇지 않는다 — 그건
추측이고, 두 발견이 정말 무관한 경우가 흔하다 (우리 실측 보드가 그렇다).

## 입력을 계약에 넣지 않는다

`ctx.git` 은 **선택 입력**이다. `datasheet` 와 같은 자리다 — 규칙이 보지만
`NEEDS` 에는 안 쓴다. 웹으로 파일 세 개를 올리는 사람에게는 이전 넷리스트가 없고,
있는 곳은 CI 다. 계약 어휘(`netlist`·`bom`·`firmware`)를 넓히면 화면에 안 쓰는
업로드 슬롯이 하나 생긴다.

이전 넷리스트가 없으면 **아무 말도 하지 않는다.** R07·R08 이 각자 할 말을 이미 한다.
"""

from __future__ import annotations

from ..netlist.d356 import Netlist
from ..text import eun
from ..types import Context, Evidence, Finding, Severity, Verdict

RULE_ID = "R10"
TITLE = "회로도 변경 후 코드 미추종 (드리프트)"
SEVERITY = Severity.CRITICAL
TIER = "차별"
NEEDS = ["netlist", "firmware"]


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    before: Netlist | None = ctx.git
    if before is None:
        return []  # 이전 상태를 모르면 무엇이 바뀌었는지도 모른다

    graph = ctx.netlist
    now: Netlist = graph.netlist
    pinmap = graph.pinmap
    firmware = ctx.firmware
    if pinmap is None or firmware is None:
        return []

    moves = _net_moves(before, now, pinmap)
    findings: list[Finding] = []

    for net, left, arrived in moves:
        # 코드가 아직 옛 핀을 쓰고 있을 때만 드리프트다.
        # 코드도 같이 옮겨갔으면 정상적으로 끝난 변경이다.
        stale = [p for p in left if firmware.find(silk=p.silk, gpio=p.gpio) is not None]
        if not stale:
            continue
        findings.append(_finding(net, stale, arrived, firmware, now))

    return findings


def _net_moves(before: Netlist, now: Netlist, pinmap):
    """네트마다 **떠난 핀**과 **새로 붙은 핀**을 짝지어 돌려준다.

    핀 하나가 다른 핀으로 바뀐 것만 본다. 네트가 통째로 사라지거나 부품이 늘어난
    것은 여기서 말할 것이 아니다 — 그건 회로도를 다시 그린 것이지 드리프트가 아니다.
    """
    out = []

    def pads_on(netlist: Netlist, net: str) -> set:
        found = set()
        for pad in pinmap.gpio_pads():
            if netlist.net_at(pad.ref, pad.pin, pad.x, pad.y) == net:
                found.add(pad.key)
        return found

    by_key = {p.key: p for p in pinmap.gpio_pads()}

    for net in now.signal_and_power_nets():
        if net not in before.nets:
            continue  # 새로 생긴 네트는 옮겨간 게 아니다
        was, is_now = pads_on(before, net), pads_on(now, net)
        left = [by_key[k] for k in sorted(was - is_now)]
        arrived = [by_key[k] for k in sorted(is_now - was)]
        if left and arrived:
            out.append((net, left, arrived))
    return out


def _finding(net: str, stale, arrived, firmware, now: Netlist) -> Finding:
    old = ", ".join(_where(p) for p in stale)
    new = ", ".join(_where(p) for p in arrived)

    lines = [
        f"이전   {net} → {old}",
        f"지금   {net} → {new}",
    ]
    for p in stale:
        where = now.net_at(p.ref, p.pin, p.x, p.y)
        lines.append(f"       {p.ref}.{p.silk} 는 이제 {where or 'N/C'} 다")

    evidence: list[Evidence] = [Evidence.netlist("\n".join(lines), [old, new])]
    for p in stale:
        use = firmware.find(silk=p.silk, gpio=p.gpio)
        if use is None:
            continue
        for call in use.calls[:2]:
            evidence.append(
                Evidence.firmware(
                    file=call.file, line=call.line, snippet=call.snippet,
                    highlight=[use.token],
                )
            )

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.FAIL,
        net=net,
        claim=(
            f"회로도에서 {eun(net)} {old} 에서 {new} 로 옮겨갔는데, "
            f"코드는 아직 {old} 을 씁니다. 회로도만 바뀌고 코드가 안 따라왔습니다."
        ),
        evidence=tuple(evidence),
        suggestion=(
            f"코드의 핀을 {new} 로 바꾸거나, 회로도를 되돌리세요. "
            f"둘 중 하나는 해야 합니다 — 지금 상태로는 보드를 만들어도 동작하지 않습니다."
        ),
        unresolved_reason=None,
    )


def _where(pad) -> str:
    return f"{pad.ref}.{pad.silk}" if pad.silk else f"{pad.ref}.{pad.pin}"
