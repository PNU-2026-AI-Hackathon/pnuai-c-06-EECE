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

#: **버스 라이브러리가 자기 핀을 직접 잡는다.** `SPI.begin()` 을 부르면 MISO·MOSI·SCK 에
#: `pinMode` 를 쓰지 않는 것이 정상이다 — 라이브러리가 주변장치에 넘긴다.
#:
#: 오픈소스 보드에서 W5500 이더넷 두 개를 SPI 로 붙인 판이 이 오탐을 6건 냈다.
#: USB 때와 같은 종류인데 **반대쪽을 못 본다** — 커넥터 핀이 `Pin_12` 라 이름이 없다.
#:
#: 그래서 네트 이름을 쓰되 **그것만으로 지우지는 않는다.** 네트 이름은 아무렇게나
#: 붙일 수 있어서 그것 하나로 경고를 없애면 진짜를 놓친다 (헌법 11절).
#: 코드가 그 버스를 실제로 쓰고 있을 때만, 그리고 **지우지 않고 미결로** 내린다.
BUS_SIGNALS: dict[str, frozenset[str]] = {
    "SPI": frozenset({"MISO", "MOSI", "SCK", "SCLK", "SS", "CIPO", "COPI"}),
    "Wire": frozenset({"SDA", "SCL"}),
}


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO 금지."""
    graph = ctx.netlist
    firmware = ctx.firmware
    netlist: Netlist = graph.netlist
    pinmap = graph.pinmap

    # 전원·접지 레일은 신호가 아니다. 코드가 만질 대상이 아니므로 대상에서 뺀다.
    signal_nets = set(graph.signal_nets())

    # **코드에서 핀을 하나도 못 읽었으면 이 규칙은 아무 말도 하지 않는다.**
    #
    # 이 규칙의 주장은 "다 읽어봤는데 이 핀이 없더라" 다. 핀을 0개 읽은 상태에서는
    # 그 주장이 성립하지 않는다 — 코드가 안 쓰는 게 아니라 **우리가 못 읽은 것**이다.
    # 실제로 ESPHome 보드(핀을 YAML 로 정한다)와 라이브러리만 든 zip 에서
    # 경고가 9건·13건 쏟아졌다. 파이프라인 3단계가 "코드가 쓰는 핀 0개" 를 이미
    # 말하고 있으므로 여기서 조용해도 숨기는 것이 아니다 (헌법 2-2 · 2-4).
    if not firmware.pins:
        return []

    # 칩을 알면 **커넥터 핀 이름이 없어도** USB 핀을 안다. 모르면 아래 상대편 이름으로 본다.
    chip = chip_of(ctx)

    # **"다 읽어봤는데 없더라" 가 이 규칙의 주장이다.** 못 읽은 자리가 있으면 그 주장이
    # 성립하지 않는다 — 그 핀이 거기 들어 있을 수 있다.
    #
    # 실제로 걸렸다. 키보드 펌웨어가 `int key_pins[] = {D4, D1, ...}` 로 20개를 적고
    # `pinMode(key_pins[i], INPUT_PULLUP)` 로 돌린다. 파서는 `key_pins[i]` 를 못 읽고
    # **그 사실을 이미 기록해 두는데**(`Unreadable`), 이 규칙이 그걸 안 봤다.
    # 보드 하나에서 확신에 찬 경고 18건이 나왔다.
    #
    # 조용히 넘기지 않는다 — 발견은 그대로 내되 **미결로 낸다** (헌법 2-2 · 2-4).
    blind = firmware.unresolved_summary if firmware.unresolved else None

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

        findings.append(
            _finding(graph, pad, net, netlist, firmware, blind or _bus_blind(firmware, net))
        )

    return findings


def _bus_blind(firmware, net: str | None) -> str | None:
    """이 네트가 **코드가 실제로 쓰는 버스**의 신호선으로 보이는가.

    두 가지가 다 맞아야 한다 — 코드가 그 라이브러리를 들여왔고, 네트 이름이
    그 버스의 신호다. 하나만으로는 아무 말도 하지 않는다.
    """
    name = (net or "").rsplit("/", 1)[-1].strip().upper()
    if not name:
        return None
    have = {h.lower() for h in firmware.includes}
    for lib, signals in BUS_SIGNALS.items():
        if lib.lower() in have and name in signals:
            return (
                f"코드가 {lib} 라이브러리를 씁니다. 그 버스의 핀은 라이브러리가 직접 잡으므로 "
                f"`pinMode` 가 없는 것이 정상일 수 있습니다 — 우리는 그 안을 못 봅니다"
            )
    return None


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


def _neighbours(netlist: Netlist, net: str, mcu_ref: str) -> str:
    """이 네트에 같이 물린 다른 부품들. **"연결된 부품" 보다 부품기호가 낫다.**

    사용자는 이 문장을 읽고 회로도를 연다. 그때 무엇을 볼지 알려주지 않으면
    네트 이름으로 다시 찾아야 한다.
    """
    others = sorted({ref for ref, _pin in netlist.connections(net) if ref != mcu_ref})
    if not others:
        return ""
    # **저항에게 "동작한다" 고 말하지 않는다.** 부품기호를 괄호로 덧붙이기만 한다 —
    # 사용자는 이 문장을 읽고 회로도를 열고, 그때 무엇을 볼지 알면 된다.
    # **조사 앞에 보간을 두지 않는다** (헌법 11절 · `test_josa_in_claims`).
    # 그래서 문장 끝에 붙는 모양으로 돌려준다 — `… 동작할 수 있습니다 (K1 · R3)`.
    if len(others) <= 3:
        return f" ({' · '.join(others)})"
    return f" ({' · '.join(others[:3])} 외 {len(others) - 3}개)"


def _gpio(pad) -> str:
    return f"GPIO{pad.gpio}" if pad.gpio is not None else "GPIO 미상"


def _finding(graph, pad, net: str, netlist: Netlist, firmware, blind: str | None) -> Finding:
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
        # **못 읽은 자리가 있으면 판정도 미결이다.** 사유만 달고 FAIL 로 두면
        # 화면에서는 그대로 결함으로 보인다 — 숨기는 것의 반대쪽 실패다.
        verdict=Verdict.FAIL if blind is None else Verdict.UNRESOLVED,
        net=net,
        claim=(
            f"회로도는 {pad.silk}({_gpio(pad)})"
            f"{'을' if eul(pad.silk).endswith('을') else '를'} {net} 로 배선해 뒀는데, "
            f"코드에는 이 핀이 한 번도 나오지 않습니다."
        ),
        evidence=tuple(evidence),
        # **지시를 먼저, 예외는 뒤에.**
        #
        # 세 문장이었고 **마지막이 첫 문장을 무효화하고 있었다** —
        # "초기화하세요 … 아직 쓸 계획이 없다면 그대로 두셔도 됩니다."
        # 읽고 나면 하라는 건지 말라는 건지 모른다. 예외를 지우지는 않는다
        # (미래용 배선은 실제로 흔하다). 다만 **뒤로 빼고 조건을 앞에 둔다.**
        #
        # "연결된 부품" 이라고 뭉뚱그리지 않고 **실제 부품기호를 짚는다** —
        # 사용자가 회로도에서 무엇을 볼지 바로 알 수 있어야 확인 비용이 준다.
        suggestion=(
            f"코드에서 {eul(pad.silk)} 초기화하세요. 초기화하지 않으면 부팅 후 이 핀이 뜬 "
            f"상태로 남아, 같은 네트에 물린 부품이 임의로 동작할 수 있습니다"
            f"{_neighbours(netlist, net, pad.ref)}. "
            f"쓸 계획이 없는 배선이라면 그대로 두셔도 됩니다."
        ),
        # 배선이 있고 코드에 없다는 것은 **다 읽었을 때만** 양쪽 다 확인된 사실이다.
        unresolved_reason=(
            None if blind is None else
            f"코드에 우리가 못 읽은 핀 표현이 있습니다 — {blind}. "
            f"{eun(pad.silk)} 거기 들어 있을 수 있어서 '안 쓴다' 고 단정하지 않습니다."
        ),
    )
