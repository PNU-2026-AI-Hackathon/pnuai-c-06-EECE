"""R02 — 회로도가 SPI 플래시 전용 핀에 배선.

**칩 표(`docs/CHIPS.md`)가 어느 핀이 플래시 전용인지 규정한다.** 코드가 아니라 표가 진실이다.

```
ESP32     GPIO6 ~ GPIO11    내장 플래시 전용. 다른 용도로 쓰면 부팅 실패
ESP32-C6  GPIO24 ~ GPIO30   내장 플래시 전용. 다른 용도 비권장
```

R01 은 같은 핀을 **코드 쪽에서** 본다 — 배선이 없어도 코드가 부르면 잡는다.
여기는 **회로도 쪽**이다. 코드가 없어도, 코드가 그 핀을 안 써도 배선 자체가 문제다.

## 외부 플래시 IC 를 오탐하지 않는다

맨칩 설계에서 플래시 핀이 실제 플래시 IC 로 가는 것은 **정상 설계**다.
이름으로는 구분할 수 없다. 토폴로지로 가른다 —

> **한 부품이 플래시 핀 여러 개에 걸쳐 있으면 그것이 플래시 IC 다.**

플래시는 CS · CLK · D0 · D1 … 여러 가닥을 한 IC 로 가져간다. 오배선은 한두 핀이
엉뚱한 곳으로 샌다. 이름이 아니라 몇 가닥인지로 본다 (A++1 과 같은 판단이다).
"""

from __future__ import annotations

from ..chips import Chip
from ..netlist.d356 import Netlist
from ..text import eun
from ..types import Context, Evidence, Finding, Severity, Verdict
from .r01_unusable_pin import chip_of

RULE_ID = "R02"
TITLE = "회로도가 SPI 플래시 전용 핀에 배선"
SEVERITY = Severity.CRITICAL
TIER = "기본"
NEEDS = ["netlist"]

#: 한 부품이 플래시 핀 이만큼에 걸쳐 있으면 플래시 IC 로 본다.
#: SPI 플래시는 최소 CS · CLK · D0 · D1 네 가닥을 쓴다.
FLASH_DEVICE_MIN_PINS = 4


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    graph = ctx.netlist
    pinmap = getattr(graph, "pinmap", None)
    chip = chip_of(ctx)
    if chip is None or not chip.spi_flash:
        return []  # 어느 칩인지 모르면 어느 핀이 플래시인지도 모른다

    netlist: Netlist = graph.netlist
    wired = _wired_flash_pads(chip, pinmap, netlist)
    if not wired:
        return []

    flash_device = _flash_device(wired, netlist)

    findings: list[Finding] = []
    for pad, net in wired:
        if flash_device is not None and flash_device in _refs_on(netlist, net):
            continue  # 이 가닥은 플래시 IC 로 간다. 정상 설계다
        findings.append(_finding(chip, pad, net, netlist, flash_device))
    return findings


def _refs_on(netlist: Netlist, net: str) -> set[str]:
    """이 네트에 붙은 부품 이름들."""
    return {ref for ref, _pin in netlist.connections(net)}


def _wired_flash_pads(chip: Chip, pinmap, netlist: Netlist) -> "list[tuple]":
    """플래시 전용 핀 중 **배선된** 것만. 미연결은 이 규칙의 대상이 아니다."""
    out = []
    if pinmap is None:
        return out
    for pad in pinmap.gpio_pads():
        if pad.gpio not in chip.spi_flash:
            continue
        net = netlist.net_at(pad.ref, pad.pin, pad.x, pad.y)
        if netlist.is_dangling(net):
            continue  # 안 뽑아놓은 핀은 정상이다
        out.append((pad, net))
    return out


def _flash_device(wired: "list[tuple]", netlist: Netlist) -> str | None:
    """플래시 핀 여러 가닥을 한꺼번에 받는 부품. 없으면 None.

    MCU 자신은 세지 않는다 — 자기 패드끼리 같은 네트에 있어도 그건 플래시 IC 가 아니다.
    """
    mcu_refs = {pad.ref for pad, _net in wired}
    tally: dict[str, int] = {}
    for _pad, net in wired:
        for ref in _refs_on(netlist, net):
            if ref in mcu_refs:
                continue
            tally[ref] = tally.get(ref, 0) + 1
    if not tally:
        return None
    ref, count = max(tally.items(), key=lambda kv: kv[1])
    return ref if count >= FLASH_DEVICE_MIN_PINS else None


def _finding(chip: Chip, pad, net: str, netlist: Netlist, flash_device: str | None) -> Finding:
    where = f"{pad.ref}.{pad.silk}" if pad.silk else f"{pad.ref}.{pad.pin}"
    token = f"GPIO{pad.gpio}"

    lines = [f"{chip.name} — {eun(token)} 내장 플래시 전용 핀이다", f"{where} → {net}"]
    for ref, pin in netlist.connections(net):
        if ref == pad.ref:
            continue
        lines.append(f"{ref}.{pin} → {net}")

    tail = ""
    if flash_device is not None:
        # 플래시 IC 는 찾았는데 이 가닥만 다른 데로 샜다. 더 강한 근거다
        tail = (
            f" 같은 보드에서 플래시 핀 대부분은 {flash_device} 로 가는데 "
            f"이 가닥만 {net} 으로 빠집니다."
        )

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.FAIL,
        net=net,
        claim=(
            f"회로도가 {where}({token}) 를 {net} 에 배선했습니다. "
            f"{chip.name} 에서 이 핀은 내장 플래시 전용이라 다른 용도로 쓰면 "
            f"부팅이 실패합니다.{tail}"
        ),
        evidence=(Evidence.netlist("\n".join(lines), [where, token]),),
        suggestion=(
            f"이 배선을 다른 GPIO 로 옮기세요. {chip.name} 의 플래시 전용 핀은 "
            f"`docs/CHIPS.md` 에 표로 있습니다."
        ),
        unresolved_reason=None,
    )
