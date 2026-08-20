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
from .r01_unusable_pin import chip_of

RULE_ID = "R08"
TITLE = "회로도에 연결됐는데 코드가 초기화 안 함"
SEVERITY = Severity.WARNING
TIER = "차별"
NEEDS = ["netlist", "firmware"]

#: **하드웨어 주변장치가 직접 모는 인터페이스의 핀 이름.**
#:
#: 이 규칙의 주장은 "코드가 안 만졌으니 그 부품이 안 움직인다" 인데,
#: USB 처럼 전용 주변장치가 모는 핀에서는 그 주장이 틀린다. 코드에
#: `pinMode(18, ...)` 이 없는 것이 **정상**이고, 오히려 만지면 인터페이스가 죽는다.
#:
#: 오픈소스 ESP32-C3 보드 4개 리비전에서 이 오탐이 리비전마다 2건씩 떴다
#: (`USB_D+` · `USB_D-`). 우리 픽스처에는 USB 를 뽑아 쓰는 보드가 없어서
#: 한 번도 안 만난 종류다 (`_docs/규모_실험.md`).
#:
#: **네트 이름을 안 믿는다.** 네트는 아무렇게나 이름 붙일 수 있다.
#: 대신 **반대쪽 핀이 스스로 밝힌 이름**을 본다 (헌법 11절 「반대쪽을 본다」) —
#: USB-C 커넥터의 핀은 그 자신이 `D+` · `D-` 다.
PERIPHERAL_PIN_NAMES = frozenset({"D+", "D-", "DP", "DM", "USB_D+", "USB_D-", "USBDP", "USBDM"})


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO 금지."""
    graph = ctx.netlist
    firmware = ctx.firmware
    netlist: Netlist = graph.netlist
    pinmap = graph.pinmap

    # 전원·접지 레일은 신호가 아니다. 코드가 만질 대상이 아니므로 대상에서 뺀다.
    signal_nets = set(graph.signal_nets())

    # 칩을 알면 **커넥터 핀 이름이 없어도** USB 핀을 안다. 모르면 아래 상대편 이름으로 본다.
    chip = chip_of(ctx)

    findings: list[Finding] = []

    for pad in pinmap.gpio_pads():
        net = netlist.net_at(pad.ref, pad.pin, pad.x, pad.y)
        if netlist.is_dangling(net):
            continue  # 배선이 없으면 이 규칙의 대상이 아니다 (R07 이 본다)
        if net not in signal_nets:
            continue  # 전원·접지에 물린 핀은 코드가 만질 것이 아니다
        if chip is not None and pad.gpio in chip.usb:
            continue  # 칩이 이 핀을 USB 로 쓴다. 코드가 안 만지는 것이 정상이다
        if _peripheral_driven(netlist, net or "", pad.ref):
            continue  # 상대편이 USB 커넥터다. 위와 같은 이유

        if firmware.find(silk=pad.silk, gpio=pad.gpio) is not None:
            continue  # 코드가 이미 쓴다

        findings.append(_finding(graph, pad, net, netlist, firmware))

    return findings


def _peripheral_driven(netlist: Netlist, net: str, mcu_ref: str) -> bool:
    """이 네트가 주변장치 인터페이스인가 — **반대쪽 핀이 스스로 밝힌다.**

    MCU 쪽 핀은 `GPIO18` 이라고만 말한다 (실리콘이 그 핀을 USB 로도 쓰는 걸
    핀 이름은 모른다). 그래서 상대편을 본다 — USB-C 커넥터의 핀은 `D-` 다.

    핀 이름이 없는 형식(IPC-D-356 은 4자에서 자른다)에서는 잘린 이름으로 본다.
    `D-` 는 두 자라 살아남는다. 못 알아보면 **기존대로 경고를 낸다** —
    조용히 통과시키지 않는다 (헌법 2-4).
    """
    for pad in netlist.connection_pads(net):
        if pad.ref == mcu_ref:
            continue
        label = (pad.name or pad.pin or "").strip().upper()
        if label in PERIPHERAL_PIN_NAMES:
            return True
    return False


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
