"""R15 — MCU 가 내는 하이 전압이 상대 부품의 입력 문턱에 못 미침.

**우리 보드에서 실제로 난 결함이 만든 규칙이다.** 합성 케이스로는 이 모양이 있는 줄도
몰랐다 — R14 가 남의 보드에서 나온 것과 같은 경로다.

## 무슨 일이 있었나

    회로도   U1.D5 (3.3V MCU) ──→ K1.IN (5V 릴레이 모듈, 액티브 로우)
    코드     digitalWrite(RELAY_PIN, HIGH);   // 끄려고 하이를 낸다

릴레이가 **켜지긴 하는데 안 꺼졌다.** 모듈 입력단이 5V 기준이라 하이로 읽히려면
5V 에 가까워야 하는데, MCU 가 낼 수 있는 것은 3.3V 가 전부다.

## R04 와 방향이 반대다

R04 는 **들어오는** 쪽을 본다 — 외부 부품 출력이 GPIO 입력 정격을 넘는가 (보드가 망가진다).
R15 는 **나가는** 쪽이다 — MCU 출력이 상대 입력 문턱에 미치는가 (안 망가지는데 안 돈다).
카탈로그에 이 방향이 통째로 없었다.

## 왜 차별 등급인가

**코드를 읽어야 성립한다.** 넷리스트는 "U1.D5 와 K1.IN 이 같은 네트" 까지만 말한다.
그 핀을 MCU 가 *출력으로 구동한다*는 것은 펌웨어에만 있다. 입력으로만 쓰는 핀이면
이 규칙의 대상이 아니다.

## 오탐을 막는 선

- **`vih_min` 을 모르면 판정하지 않는다.** 5V 부품이라고 다 5V 문턱인 게 아니다 —
  TTL 호환 입력은 2.0V 면 하이로 읽는다. 그게 이 규칙에서 제일 흔한 오탐이 될 자리다
- **오픈드레인으로 몰면 대상이 아니다.** 그때 하이 레벨은 MCU 가 아니라 풀업이 정한다
- **상대가 이 네트에서 전원을 받는 중이면 대상이 아니다** (`VCC` 핀이 걸린 경우).
  R11 에서 같은 자리에 데였다
- 상대 도메인이 MCU 와 같거나 낮으면 볼 것이 없다
"""

from __future__ import annotations

from ..datasheet.facts import OPEN_DRAIN, OUTPUT_TYPE, VIH_MIN
from ..netlist.graph import (
    DOMAIN_EPSILON_V,
    SUPPLY_PIN_PATTERN,
    Graph,
    format_volts,
)
from ..text import eul, eun, i_ga
from ..types import Context, Evidence, Finding, Severity, Verdict
from ._clearance import ask, ask_input_threshold, number

RULE_ID = "R15"
TITLE = "MCU 출력 하이가 상대 부품의 입력 문턱에 못 미침"
SEVERITY = Severity.CRITICAL
TIER = "차별"
NEEDS = ["netlist", "firmware"]

#: 펌웨어가 이 핀을 출력으로 몬다고 말하는 값
DIRECTION_OUTPUT = "output"

#: **상대 핀이 스스로 출력이라고 밝힌 이름.**
#:
#: 이 규칙의 전제는 "상대가 이 핀을 *입력으로 읽는다*" 이다. 핀 이름이 `OUT` 이면
#: 그 전제가 안 선다 — 물어볼 질문 자체가 아니다.
#:
#: 실제로 데였다. 센서의 `U2.OUT` 을 보고 "5V 로 도는 부품의 **입력**이라" 고 적었는데,
#: 넷리스트가 출력이라고 말하고 있었다 (헌법 11절 「단정하지 않는다」).
#: 그 자리의 진짜 문제는 다른 것이다 — 코드가 센서 출력에 자기 출력을 물렸다.
#: 그건 R07·R08·R10 이 드리프트로 잡는다.
#:
#: **모르면 건너뛰지 않는다.** 이름이 없는 핀(`pad-`)은 그대로 본다 —
#: 입력일 수도 있으므로 "확인 필요" 로 남긴다.
OUTPUT_PIN_NAMES = ("OUT", "DOUT", "SDO", "MISO", "TX", "TXD")


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    graph: Graph = ctx.netlist
    firmware = ctx.firmware
    if firmware is None or not firmware.pins:
        return []

    findings: list[Finding] = []
    for mcu, net, use in _driven_nets(graph, firmware):
        mcu_v = graph.domain(mcu).volts
        if mcu_v is None:
            continue

        for ref in graph.refs_on(net):
            if ref == mcu:
                continue
            other = graph.domain(ref)
            if not other.known or other.volts - mcu_v <= DOMAIN_EPSILON_V:
                continue

            pin = graph.pin_on_net(ref, net)
            if pin and SUPPLY_PIN_PATTERN.match(pin):
                continue  # 여기서 전원을 받는 중이다. 입력 문턱을 물을 자리가 아니다
            if _is_output_pin(pin):
                continue  # 상대가 스스로 출력이라고 말한다. 입력 문턱을 물을 자리가 아니다

            findings.append(_judge(ctx, graph, net, mcu, mcu_v, ref, other.volts, use))

    return findings


def _is_output_pin(pin: str | None) -> bool:
    """이 핀이 **스스로 출력이라고 밝히는가.** 모르면 False (그대로 본다).

    이 규칙의 전제는 "상대가 이 핀을 *입력으로 읽는다*" 다. 핀 이름이 `OUT` 이면
    그 전제가 안 선다 — 물어볼 질문 자체가 아니다.

    실제로 데였다. 센서의 `U2.OUT` 을 보고 "5V 로 도는 부품의 **입력**이라" 고 적었는데
    넷리스트가 출력이라고 말하고 있었다 (헌법 11절 「단정하지 않는다」).
    그 자리의 진짜 문제는 다른 것이다 — 코드가 센서 출력에 자기 출력을 물렸다.
    그건 R07·R08·R10 이 드리프트로 잡는다.
    """
    if not pin:
        return False
    name = pin.strip().upper().lstrip("~/")
    return any(
        name == token or name.startswith(token + "_") or name.startswith(token + "0")
        for token in OUTPUT_PIN_NAMES
    )


def _driven_nets(graph: Graph, firmware):
    """코드가 **출력으로 모는** 핀이 물린 네트들 — `(MCU 부품, 네트, 사용)`.

    **두 길로 찾는다. 형식마다 손에 쥔 것이 다르다.**

    1. 핀맵이 풀렸으면 그것을 쓴다. IPC-D-356 은 핀 이름을 4자로 자르므로
       (`SDIO` ×3) 좌표로 복원한 핀맵만이 `D5` 가 어느 패드인지 안다
    2. 안 풀렸으면 **핀 이름으로 직접 맞춘다.** 회로도 넷리스트는 `D5` 를 그대로
       실어 주므로 복원이 필요 없다

    1번만 있으면 회로도 넷리스트로 올린 보드에서 이 규칙이 통째로 침묵한다 —
    핀맵은 모듈 핀아웃 DB에 있는 보드에서만 풀리기 때문이다.
    """
    seen: set[tuple[str, str]] = set()

    for use in firmware.pins:
        if use.direction != DIRECTION_OUTPUT:
            continue  # 입력으로만 쓰는 핀은 이 규칙의 대상이 아니다

        # 1. 핀맵
        for pad in graph.pinmap.gpio_pads():
            same = (use.gpio is not None and pad.gpio == use.gpio) or (
                use.silk and pad.silk == use.silk
            )
            if not same:
                continue
            net = graph.netlist.net_at(pad.ref, pad.pin, pad.x, pad.y)
            if net and not graph.netlist.is_dangling(net) and (pad.ref, net) not in seen:
                seen.add((pad.ref, net))
                yield pad.ref, net, use

        # 2. 핀 이름
        if not use.silk:
            continue
        for ref in graph.netlist.parts:
            nets = graph.pins_of(ref).get(use.silk)
            if not nets:
                continue
            for net in nets:
                if graph.netlist.is_dangling(net) or (ref, net) in seen:
                    continue
                seen.add((ref, net))
                yield ref, net, use


def _judge(ctx, graph, net, mcu, mcu_v, ref, other_v, use) -> Finding:
    """`vih_min` 을 알면 판정하고, 모르면 무엇이 있어야 풀리는지 적는다."""
    drive = ask(ctx, ref, OUTPUT_TYPE, what="입력단 구동 방식")
    # `vih_min` 이 정석이고, 없으면 `io_level` 을 본다 — 모듈 데이터시트는
    # 문턱 규격을 잘 안 주고 "IO 레벨 5V" 라고만 적는 일이 흔하다.
    vih = ask_input_threshold(ctx, ref)

    mcu_pin = graph.display_pin(mcu, net) or graph.pin_on_net(mcu, net) or "?"
    other_pin = graph.pin_on_net(ref, net) or "?"
    mcu_token = f"{mcu}.{mcu_pin}"
    other_token = f"{ref}.{other_pin}"

    lines = [
        f"{mcu_token} → {net}   ({mcu} 전원 도메인 = {format_volts(mcu_v)}V)",
        f"{other_token} → {net}   ({ref} 전원 도메인 = {format_volts(other_v)}V)",
    ]
    evidence: list[Evidence] = [Evidence.netlist("\n".join(lines), [mcu_token, other_token, net])]

    where = use.definition or (use.calls[0] if use.calls else None)
    if where is not None:
        evidence.append(
            Evidence.firmware(
                file=where.file, line=where.line, snippet=where.snippet,
                highlight=[s for s in use.symbols][:2],
            )
        )

    # **상대가 이 핀을 입력으로 받는지 단정하지 않는다.** 넷리스트에 핀 방향이 없다.
    # 조건절로 적으면 사용자가 먼저 그것부터 확인하고, 아니면 그냥 넘긴다.
    head = (
        f"코드가 {eul(mcu_token)} 출력으로 몹니다. 이 핀은 {format_volts(other_v)}V 로 도는 "
        f"{ref} 의 {other_token} 에 이어져 있는데, {i_ga(ref)} 이 핀을 입력으로 받는다면 "
        f"MCU 가 낼 수 있는 {format_volts(mcu_v)}V 가 하이로 읽히는지 확인해야 합니다."
    )

    threshold = number(vih)
    if threshold is not None:
        cite = vih.evidence()
        if cite is not None:
            evidence.append(cite)
        if mcu_v + DOMAIN_EPSILON_V < threshold:
            return Finding(
                rule=RULE_ID, title=TITLE, tier=TIER, severity=SEVERITY,
                verdict=Verdict.FAIL, net=net,
                claim=(
                    f"코드가 {eul(mcu_token)} 출력으로 몰지만, {eun(ref)} 하이로 읽으려면 "
                    f"{format_volts(threshold)}V 가 필요합니다. MCU 는 "
                    f"{format_volts(mcu_v)}V 까지밖에 못 냅니다 — "
                    f"이 신호는 **하이가 되지 않습니다.**"
                ),
                evidence=tuple(evidence),
                suggestion=(
                    f"레벨 시프터나 트랜지스터를 사이에 넣으세요. "
                    f"{ref} 쪽 입력을 {format_volts(other_v)}V 로 올려 줘야 합니다. "
                    f"코드만 고쳐서는 해결되지 않습니다."
                ),
                unresolved_reason=None,
            )
        return Finding(
            rule=RULE_ID, title=TITLE, tier=TIER, severity=SEVERITY,
            verdict=Verdict.PASS, net=net,
            claim=(
                f"{eun(mcu_token)} {format_volts(other_v)}V 부품인 {ref} 의 입력을 몹니다. "
                f"다만 {ref}({vih.mpn}) 의 입력 하이 문턱이 {format_volts(threshold)}V 로 확인돼 "
                f"MCU 의 {format_volts(mcu_v)}V 로 충분합니다."
            ),
            evidence=tuple(evidence),
            suggestion=f"조치할 것이 없습니다. {ref} 의 부품번호가 바뀌면 이 판정도 다시 해야 합니다.",
            unresolved_reason=None,
        )

    # 오픈드레인이면 하이 레벨을 MCU 가 정하지 않는다 — 물어볼 질문 자체가 아니다
    if drive.fact is not None and drive.fact.usable and drive.fact.value == OPEN_DRAIN:
        return Finding(
            rule=RULE_ID, title=TITLE, tier=TIER, severity=SEVERITY,
            verdict=Verdict.PASS, net=net,
            claim=(
                f"{eun(mcu_token)} {format_volts(other_v)}V 부품인 {ref} 의 입력을 몹니다. "
                f"다만 {ref} 의 입력단이 오픈드레인으로 확인돼 하이 레벨은 MCU 가 아니라 "
                f"풀업이 정합니다."
            ),
            evidence=tuple(evidence + ([drive.evidence()] if drive.evidence() else [])),
            suggestion="조치할 것이 없습니다.",
            unresolved_reason=None,
        )

    return Finding(
        rule=RULE_ID, title=TITLE, tier=TIER, severity=SEVERITY,
        verdict=Verdict.UNRESOLVED, net=net,
        claim=head,
        evidence=tuple(evidence),
        suggestion=(
            f"{ref} 의 데이터시트에서 **입력 하이 문턱(V_IH)** 을 확인하세요. "
            f"{format_volts(mcu_v)}V 이하면 문제가 없고, 그보다 높으면 레벨 시프터가 필요합니다."
        ),
        unresolved_reason=vih.missing or f"{i_ga(ref)} 입력 하이 문턱(V_IH)을 아직 모릅니다.",
    )


