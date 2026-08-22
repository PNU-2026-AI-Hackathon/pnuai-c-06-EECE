"""R07 — 코드가 쓰는 핀이 회로도에 미연결.

차별 등급의 중심. 회로도만 보는 도구도, 코드만 보는 도구도 못 잡는다.
컴파일도 되고 업로드도 되는데 보드가 도착하면 안 켜지는 종류다.

**데이터시트를 한 번도 읽지 않고 확정된다.** 부품이 뭔지 몰라도
"이 패드에 배선이 없다"는 사실은 그 자체로 확정이다 — `unresolved_reason` 은 None 이다.

근거는 **실제로 존재하는 줄만** 가리킨다. 상수가 선언된 자리와 그 핀을 실제로 만지는
자리 두 곳을 함께 준다. 발췌에 없는 주석을 지어 붙이지 않는다 — 사용자가 그 줄을 열어본다.
"""

from __future__ import annotations

from ..firmware.arduino import DIRECTION_INPUT, DIRECTION_OUTPUT
from ..netlist.d356 import Netlist
from ..text import eul
from ..types import Context, Evidence, Finding, Severity, Verdict

RULE_ID = "R07"
TITLE = "코드가 쓰는 핀이 회로도에 미연결"
SEVERITY = Severity.CRITICAL
TIER = "차별"
NEEDS = ["netlist", "firmware"]

DIRECTION_WORDS = {
    DIRECTION_OUTPUT: "출력으로 구동합니다",
    DIRECTION_INPUT: "입력으로 읽습니다",
}
DIRECTION_FALLBACK = "사용합니다"

#: 방향을 말해 주지 않는 함수. 대표 사용 자리를 고를 때 뒤로 민다.
WEAK_CALLS = ("pinMode",)


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO 금지."""
    graph = ctx.netlist
    firmware = ctx.firmware
    netlist: Netlist = graph.netlist
    pinmap = graph.pinmap

    findings: list[Finding] = []

    for use in firmware.pins:
        pad = pinmap.find(silk=use.silk, gpio=use.gpio)
        if pad is None:
            # **회로도 넷리스트에는 안 쓰는 핀이 아예 안 나온다.**
            #
            # IPC-D-356 은 헤더 핀을 다 싣고 안 이은 것은 N/C 로 온다. 회로도는
            # 쓰는 핀만 그린다 — 그래서 "미연결" 이 *패드가 있는데 네트가 없음* 이
            # 아니라 *패드가 아예 없음* 으로 나타난다. 같은 사실인데 모양이 다르다.
            #
            # 모듈을 알아봤다면 그 핀이 **있다는 것을 안다.** 있는 핀을 코드가 쓰는데
            # 회로도가 한 번도 안 부르면 그건 안 이어진 것이다.
            # 모듈을 못 알아봤으면 그대로 넘어간다 — 모르면 판정하지 않는다.
            missing = _absent_pin(graph, use)
            if missing is not None:
                findings.append(_finding_absent(use, missing, netlist))
            continue

        net = netlist.net_at(pad.ref, pad.pin, pad.x, pad.y)
        if not netlist.is_dangling(net):
            continue

        findings.append(_finding(use, pad, netlist, pinmap))

    return findings


def _absent_pin(graph, use) -> "tuple[str, str, int] | None":
    """코드가 쓰는 핀이 **모듈에는 있는데 회로도에는 없는가.** `(부품, 실크, GPIO)`.

    알아본 모듈이 있어야 성립한다. 모듈을 모르면 그 부품에 그 핀이 있는지도 모르므로
    아무 말도 하지 않는다 (헌법 2-2).
    """
    from ..chips import MODULES

    pinmap = graph.pinmap
    for ref, module_id in pinmap.modules_matched.items():
        module = MODULES.get(module_id)
        if module is None:
            continue
        silk_to_gpio = module.silk_to_gpio
        for silk, gpio in silk_to_gpio.items():
            same = (use.silk and use.silk == silk) or (use.gpio is not None and use.gpio == gpio)
            if not same:
                continue
            # 회로도가 이 핀을 한 번이라도 부르는가
            if any(i.ref == ref and i.silk == silk for i in pinmap.all()):
                return None  # 있다. 그럼 위쪽 경로가 볼 일이다
            return (ref, silk, gpio)
    return None


def _finding_absent(use, missing: "tuple[str, str, int]", netlist: Netlist) -> Finding:
    """모듈에는 있는데 회로도가 한 번도 안 부른 핀."""
    ref, silk, gpio = missing
    action = DIRECTION_WORDS.get(use.direction, DIRECTION_FALLBACK)
    symbol = use.symbols[0] if use.symbols else use.token
    token = f"{ref}.{silk}"

    evidence = [
        Evidence.netlist(
            f"{token} (GPIO{gpio})\n"
            f"  → 회로도에 이 핀이 한 번도 나오지 않습니다\n"
            f"\n"
            f"회로도 넷리스트는 **쓰는 핀만 싣습니다.** 이 모듈에 {silk} 핀이 있는 것은 "
            f"핀아웃 표로 알고 있습니다 (docs/CHIPS.md).",
            [token],
        )
    ]
    for where in (use.definition, use.calls[0] if use.calls else None):
        if where is not None:
            evidence.append(
                Evidence.firmware(
                    file=where.file, line=where.line, snippet=where.snippet,
                    highlight=[symbol],
                )
            )

    return Finding(
        rule=RULE_ID, title=TITLE, tier=TIER, severity=SEVERITY,
        verdict=Verdict.FAIL, net=None,
        claim=(
            f"코드가 {silk}(GPIO{gpio}) 핀을 {action}. 그런데 회로도에는 이 핀이 "
            f"한 번도 나오지 않습니다 — 아무 데도 이어져 있지 않습니다."
        ),
        evidence=tuple(evidence),
        suggestion=(
            f"회로도에서 {eul(silk)} 배선하거나, 코드에서 {symbol} 사용을 지우세요. "
            f"지금 상태로는 보드를 발주해도 이 핀은 동작하지 않습니다."
        ),
        unresolved_reason=None,
    )


def _representative(use):
    """그 핀으로 실제로 무엇을 하는지 가장 잘 보여주는 호출."""
    strong = [c for c in use.calls if c.function not in WEAK_CALLS]
    return (strong or list(use.calls))[0]


def _finding(use, pad, netlist: Netlist, pinmap) -> Finding:
    action = DIRECTION_WORDS.get(use.direction, DIRECTION_FALLBACK)
    gpio = f"GPIO{pad.gpio}" if pad.gpio is not None else "GPIO 미상"
    symbol = use.symbols[0] if use.symbols else use.token

    # ------------------------------------------------------------- 회로도 근거
    lines = [
        f"{pad.ref}.{pad.silk} ({gpio}, 패드명 {pad.pin})",
        "  → N/C   연결된 네트 없음",
    ]
    context: list[str] = []
    wired = [
        f"{p.silk} → {n}"
        for p in pinmap.gpio_pads()
        if p.ref == pad.ref
        for n in [netlist.net_at(p.ref, p.pin, p.x, p.y)]
        if not netlist.is_dangling(n)
    ]
    if wired:
        context.append(f"같은 헤더에서 배선된 핀: {', '.join(wired)}")

    twins = [i for i in pinmap.all() if i.ref == pad.ref and i.pin == pad.pin]
    if len(twins) > 1:
        context.append(
            f"넷리스트에서 이름이 {pad.pin} 로 뭉친 패드가 {len(twins)}개입니다. "
            f"좌표로 {eul(pad.silk)} 특정했습니다."
        )

    if context:
        lines.append("")
        lines.extend(context)

    evidence = [Evidence.netlist("\n".join(lines), [f"{pad.ref}.{pad.silk}", "N/C"])]

    # -------------------------------------------------------------- 코드 근거
    # 두 자리 다 실제 소스 줄이다. 상수가 어디서 이 핀이 됐는지 + 그 핀으로 무엇을 하는지.
    if use.definition is not None:
        evidence.append(
            Evidence.firmware(
                file=use.definition.file,
                line=use.definition.line,
                snippet=use.definition.snippet,
                highlight=[symbol],
            )
        )
    call = _representative(use)
    evidence.append(
        Evidence.firmware(
            file=call.file, line=call.line, snippet=call.snippet, highlight=[symbol]
        )
    )

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.FAIL,
        net=None,
        claim=(
            f"코드가 {pad.silk}({gpio}) 핀을 {action}. "
            f"그런데 회로도에서 이 핀은 아무 네트에도 연결돼 있지 않습니다."
        ),
        evidence=tuple(evidence),
        suggestion=(
            f"{pad.silk}에 배선을 추가하거나, 코드에서 {symbol} 사용을 지우세요. "
            "지금 상태로는 보드를 발주해도 이 핀은 동작하지 않습니다."
        ),
        # 부품을 몰라도 "배선이 없다"는 확정이다. 보류하지 않는다.
        unresolved_reason=None,
    )
