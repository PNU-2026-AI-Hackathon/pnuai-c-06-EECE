"""R03 — 스트래핑 핀이 전원·접지에 직결.

**칩 표(`docs/CHIPS.md`)가 어느 핀이 스트래핑인지 규정한다.**

```
ESP32     GPIO0 · 2 · 5 · 12 · 15    부팅 시 레벨이 부팅 모드를 결정
ESP32-C6  GPIO4 · 5 · 8 · 9 · 15     GPIO8·9 는 부팅 모드, GPIO15 는 JTAG 소스 선택
```

스트래핑 핀은 **부팅 순간의 전압으로 칩의 동작 모드를 정한다.** 그 핀이 전원 레일이나
접지에 직결돼 있으면 모드가 한쪽으로 굳는다. 대표적으로 ESP32 는 GPIO0 가 접지에 묶이면
매번 다운로드 모드로 부팅하고, GPIO12 가 전원에 묶이면 플래시 전압을 1.8V 로 잘못 잡아
보드가 아예 안 뜬다.

## 무엇을 잡고 무엇을 안 잡나

**직결만 잡는다.** 패드가 전원·접지 네트에 그대로 올라가 있는 경우다.

저항·스위치를 거치면 그 패드는 **다른 네트**에 있으므로 여기 안 걸린다. 그게 맞다 —
풀업 저항이나 부트 버튼은 정상 설계이고, 그것까지 경고하면 거의 모든 ESP32 보드에서
오탐이 난다. 린터는 못 잡아서가 아니라 잘못 잡아서 꺼진다 (CLAUDE.md 2-3).

R01 은 같은 핀을 코드 쪽에서 본다 — 코드가 그 핀을 구동하는 경우다. 여기는 배선이다.
"""

from __future__ import annotations

from ..chips import Chip
from ..netlist.d356 import Netlist
from ..netlist.graph import GND_PATTERN, local_name
from ..text import eun
from ..types import Context, Evidence, Finding, Severity, Verdict
from .r01_unusable_pin import chip_of

RULE_ID = "R03"
TITLE = "스트래핑 핀이 전원·접지에 직결"
SEVERITY = Severity.WARNING
TIER = "기본"
NEEDS = ["netlist"]


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    graph = ctx.netlist
    pinmap = getattr(graph, "pinmap", None)
    chip = chip_of(ctx)
    if chip is None or not chip.strapping:
        return []  # 어느 칩인지 모르면 어느 핀이 스트래핑인지도 모른다
    if pinmap is None:
        return []

    netlist: Netlist = graph.netlist
    findings: list[Finding] = []

    for pad in pinmap.gpio_pads():
        if pad.gpio not in chip.strapping:
            continue
        net = netlist.net_at(pad.ref, pad.pin, pad.x, pad.y)
        if netlist.is_dangling(net):
            continue  # 안 뽑아놓은 핀은 정상이다
        level = _tie_level(graph, net)
        if level is None:
            continue  # 신호 네트다. 저항·스위치를 거치면 여기 안 온다
        findings.append(_finding(chip, pad, net, level, netlist))

    return findings


def _tie_level(graph, net: str) -> str | None:
    """이 네트가 부팅 레벨을 고정하는가. `"LOW"` · `"HIGH"` · 아니면 None."""
    if GND_PATTERN.match(local_name(net)):
        return "LOW"
    if graph.is_power_rail(net):
        return "HIGH"
    return None


def _finding(chip: Chip, pad, net: str, level: str, netlist: Netlist) -> Finding:
    where = f"{pad.ref}.{pad.silk}" if pad.silk else f"{pad.ref}.{pad.pin}"
    token = f"GPIO{pad.gpio}"
    held = "접지에 묶여 항상 LOW" if level == "LOW" else f"{net} 에 묶여 항상 HIGH"

    lines = [f"{chip.name} — {eun(token)} 스트래핑 핀이다", f"{where} → {net}"]
    others = [f"{ref}.{pin}" for ref, pin in netlist.connections(net) if ref != pad.ref]
    if others:
        lines.append(f"같은 네트: {', '.join(others[:6])}")

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.FAIL,
        net=net,
        claim=(
            f"회로도가 {where}({token}) 를 {net} 에 직결했습니다. "
            f"{chip.name} 에서 이 핀은 부팅 순간의 레벨로 동작 모드를 정하는데, "
            f"지금 배선으로는 {held} 입니다. 부팅 모드가 한쪽으로 굳습니다."
        ),
        evidence=(Evidence.netlist("\n".join(lines), [where, token, net]),),
        suggestion=(
            "레벨을 정해야 한다면 직결 대신 풀업·풀다운 저항을 거치세요. "
            "그러면 필요할 때 다른 값으로 덮을 수 있습니다. "
            f"{chip.name} 의 스트래핑 핀은 `docs/CHIPS.md` 에 표로 있습니다."
        ),
        unresolved_reason=None,
    )
