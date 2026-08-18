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
            # 이 핀이 보드의 어느 패드인지 모른다. 모르면 판정하지 않는다.
            # 몇 개를 못 짚었는지는 파이프라인 3단계에 사유와 함께 실린다.
            continue

        net = netlist.net_at(pad.ref, pad.pin, pad.x, pad.y)
        if not netlist.is_dangling(net):
            continue

        findings.append(_finding(use, pad, netlist, pinmap))

    return findings


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
