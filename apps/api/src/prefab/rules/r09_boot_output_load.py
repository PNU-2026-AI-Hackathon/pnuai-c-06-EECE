"""R09 — 부팅 시 출력 나오는 핀에 부하 연결.

**칩 표(`docs/CHIPS.md`)가 어느 핀이 부팅 때 스스로 신호를 내는지 규정한다.**

```
ESP32     GPIO0 · 1 · 3 · 5 · 14 · 15   GPIO1 은 부팅 로그(U0TXD), 나머지는 HIGH/PWM
ESP32-C6  GPIO16                        U0TXD — 부팅 로그가 115200bps 로 나간다
```

리셋 직후 몇백 밀리초 동안 이 핀들은 **코드와 무관하게** 신호를 낸다. 부트 ROM 이
로그를 찍고, 스트래핑 결과에 따라 레벨이 튄다. `setup()` 은 그게 다 끝난 뒤에 돈다 —
**펌웨어로는 막을 수 없다.** 릴레이 IN 이 여기 붙어 있으면 보드에 전원을 넣을 때마다
릴레이가 딸깍거리고, 모터 드라이버 EN 이면 축이 움찔한다.

## 무엇을 잡고 무엇을 안 잡나

**직결된 구동 부품만 잡는다.** R03 과 같은 좁은 경계다.

- **잡는다** — 릴레이(`K`) · 트랜지스터(`Q`) · 모터(`M`) · 부저(`BZ`) · 스피커(`LS`).
  부품기호 접두어는 IEEE 315 / ASME Y14.44 표준이고, 이 리포는 이미 같은 관례로
  수동 소자를 가른다 (`graph.PASSIVE_REF_PATTERN`).
- **안 잡는다** — 커넥터(`J`). 부팅 로그 핀을 헤더로 빼는 것은 **정상 설계**다.
  시리얼 콘솔이 바로 그것이다. 이걸 잡으면 거의 모든 개발보드에서 오탐이 난다.
- **안 잡는다** — 저항·커패시터만 붙은 네트. 직렬 저항은 오히려 완화책이다.
- **안 잡는다** — 전원·접지에 직결된 경우. 그건 R03 의 영역이고, 여기서도 띄우면
  같은 배선을 두 번 읽게 된다.

## 부품을 모르면 모른다고 한다

부품기호가 `K1` 이면 릴레이라는 **관례**는 알지만 그 모듈의 IN 이 실제로 어떤
입력인지는 데이터시트가 답한다. BOM 으로 부품번호가 확인되지 않으면 판정은 그대로
두되 `unresolved_reason` 에 무엇을 내면 풀리는지 적는다 (CLAUDE.md 2-2).
"""

from __future__ import annotations

import re

from ..chips import Chip
from ..netlist.d356 import Netlist
from ..netlist.graph import GND_PATTERN, local_name
from ..text import eun, i_ga
from ..types import Context, Evidence, Finding, Severity, Verdict
from .r01_unusable_pin import chip_of

RULE_ID = "R09"
TITLE = "부팅 시 출력 나오는 핀에 부하 연결"
SEVERITY = Severity.WARNING
TIER = "기본"
NEEDS = ["netlist"]

#: 핀이 토글하면 **실제로 움직이는** 부품. 부품기호 접두어 표준(IEEE 315)을 따른다.
#: 커넥터(J)·수동 소자(R·C·L)는 일부러 뺐다 — 위 「무엇을 안 잡나」 참고.
ACTUATOR_REF_PATTERN = re.compile(r"^(K|Q|M|BZ|LS|RLY|SSR)\d", re.I)

#: 부품기호 접두어 → 사람이 읽는 이름
ACTUATOR_NAMES: dict[str, str] = {
    "K": "릴레이", "RLY": "릴레이", "SSR": "SSR",
    "Q": "트랜지스터", "M": "모터", "BZ": "부저", "LS": "스피커",
}


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    graph = ctx.netlist
    pinmap = getattr(graph, "pinmap", None)
    chip = chip_of(ctx)
    if chip is None or not chip.boot_output:
        return []  # 어느 칩인지 모르면 어느 핀이 부팅 때 출력인지도 모른다
    if pinmap is None:
        return []

    netlist: Netlist = graph.netlist
    findings: list[Finding] = []

    for pad in pinmap.gpio_pads():
        if pad.gpio not in chip.boot_output:
            continue
        net = netlist.net_at(pad.ref, pad.pin, pad.x, pad.y)
        if netlist.is_dangling(net):
            continue  # 안 뽑아놓은 핀은 정상이다
        if GND_PATTERN.match(local_name(net)) or graph.is_power_rail(net):
            continue  # 레일 직결은 R03 이 본다. 같은 배선을 두 번 읽히지 않는다
        loads = [
            ref for ref in graph.refs_on(net)
            if ref != pad.ref and ACTUATOR_REF_PATTERN.match(ref)
        ]
        if not loads:
            continue  # 커넥터·수동 소자만 붙은 것은 정상이다
        findings.append(_finding(chip, pad, net, loads, graph, ctx.bom))

    return findings


def _actuator_name(ref: str) -> str:
    """부품기호 접두어를 사람 말로. 모르면 '구동 부품' 이라고만 한다."""
    letters = "".join(c for c in ref if c.isalpha()).upper()
    for key in sorted(ACTUATOR_NAMES, key=len, reverse=True):
        if letters.startswith(key):
            return ACTUATOR_NAMES[key]
    return "구동 부품"


def _why_it_outputs(chip: Chip, gpio: int) -> str:
    if chip.boot_log_tx == gpio:
        return "부팅 로그(UART0 TX)가 115200bps 로 나갑니다"
    return "부팅·리셋 순간에 HIGH 또는 PWM 이 나갑니다"


def _unresolved(loads: list[str], bom) -> str | None:
    """부품번호가 확인 안 된 부하를 그대로 적는다. 판정은 바꾸지 않는다."""
    if bom is None:
        return f"{' · '.join(loads)} 미식별 — BOM 필요"
    unknown = [ref for ref in loads if not bom.mpn_of(ref)]
    if unknown:
        return f"{' · '.join(unknown)} 부품번호 없음 — BOM 에 채우면 입력 규격으로 확정됩니다"
    return None


def _finding(chip: Chip, pad, net: str, loads: list[str], graph, bom) -> Finding:
    where = f"{pad.ref}.{pad.silk}" if pad.silk else f"{pad.ref}.{pad.pin}"
    token = f"GPIO{pad.gpio}"
    reason = _why_it_outputs(chip, pad.gpio)
    named = " · ".join(f"{ref}({_actuator_name(ref)})" for ref in loads)
    # 조사는 마지막 부품기호에 맞춘다 (헌법 11절).
    named_ja = i_ga(named) if len(loads) == 1 else named + " 이(가)"

    lines = [f"{chip.name} — {eun(token)} 부팅 때 출력이 나오는 핀이다", f"{where} → {net}"]
    for ref in loads:
        pin = graph.ref_pin(ref, net)
        lines.append(f"{pin} → {net}   ({_actuator_name(ref)})")

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.FAIL,
        net=net,
        claim=(
            f"{where}({token}) 에 {named_ja} 직결돼 있는데, "
            f"{chip.name} 에서 이 핀은 {reason}. "
            "코드가 돌기 전에 나오는 신호라 펌웨어로는 막을 수 없습니다 — "
            "전원을 넣을 때마다 한 번씩 동작합니다."
        ),
        evidence=(Evidence.netlist("\n".join(lines), [where, token, net, *loads]),),
        suggestion=(
            "부팅 때 출력이 안 나오는 핀으로 옮기는 것이 가장 확실합니다. "
            "핀을 못 바꾸면 부하 쪽에 풀다운(또는 반전 입력이면 풀업)을 넣어 "
            "부팅 구간 동안 비활성으로 붙잡아 두세요. "
            f"{chip.name} 의 핀 표는 `docs/CHIPS.md` 에 있습니다."
        ),
        unresolved_reason=_unresolved(loads, bom),
    )


def blocked(ctx) -> str | None:
    """어느 칩인지 모르면 이 규칙은 **시작도 못 한다.**

    조용히 빈 목록을 돌려주면 화면에 "규칙 실행됨" 으로 세어져서, 사용자는 검사해서
    깨끗한 줄 안다. 실제로는 아무것도 안 본 것이다 (헌법 2-4).

    푸는 법은 사용자가 할 수 있는 일로 적는다 — 우리 표에 없는 칩이면 그것도 말한다.
    """
    chip = chip_of(ctx)
    if chip is None:
        return (
            "어느 칩인지 알아내지 못했습니다 — 부품번호(MPN)를 BOM 이나 회로도 심볼에 "
            "채우면 판정합니다. 채워져 있는데도 이 문구가 보이면 그 칩이 아직 우리 표에 "
            "없는 것입니다 (docs/CHIPS.md)."
        )
    if not chip.boot_output:
        # **칩은 알아냈는데 그 칸이 비어 있다.** 둘 중 하나인데 둘 다 「판정 안 함」이다.
        # 표에 이유를 적어 뒀다 — RP2040 은 진짜로 없고, C6 의 부팅 출력은 못 찾은 것이다.
        return f"{chip.name} 에 대해 이 규칙이 볼 핀 목록이 표에 없습니다 (docs/CHIPS.md)."
    return None
