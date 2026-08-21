"""R14 — 같은 이름의 핀 상수가 서로 다른 핀을 가리킨다.

**이 규칙은 실제 오픈소스 보드에서 찾은 결함으로 만들었다.** 합성 케이스로는
이런 모양이 있는 줄도 몰랐다 (`_docs/규모_실험.md` — 유성 자문 반영).

`FForzano/xgsail-e1` (Apache-2.0) 에서 실제로 이랬다 —

    User_Setup.h:15   #define TFT_BL      19   // Swapped with MISO to match soldered E1 wiring
    config.h:22       #define TFT_BL_PIN  25   // Backlight PWM
    edge.ino:265      ledcAttach(TFT_BL_PIN, TFT_BL_PWM_FREQ, TFT_BL_PWM_RES);

배선이 바뀌어 백라이트가 GPIO19 로 옮겨갔고 개발자가 `User_Setup.h` 는 고치면서
**주석까지 남겼는데 `config.h` 가 안 따라왔다.** 그래서 코드가 GPIO25 에 PWM 을
붙이는데, 그 핀은 회로도상 SPI MISO 다.

**넷리스트가 없어도 잡힌다.** 코드 안에서 이미 모순이라서다. 회로도가 있으면
어느 쪽이 맞는지도 같이 실어 준다 — 다만 그건 근거일 뿐 판정 근거는 아니다.

**오탐을 막는 선:**

- 이름을 정규화한 뒤 **완전히 같을 때만** 본다. `TFT_BL` 과 `TFT_BLK` 는 다른 이름이다
- 번호가 다를 때만 낸다. 같은 핀을 두 이름으로 부르는 것은 정상이다
  (`LED_PIN` 과 `LED` 가 둘 다 2번이면 문제가 아니다)
- 접미 하나만 뗀다 (`_PIN` · `_GPIO` · `_IO`). 더 떼면 서로 다른 이름이 뭉친다
"""

from __future__ import annotations

import re
from collections import OrderedDict

from ..text import eul, i_ga
from ..types import Context, Evidence, Finding, Severity, Verdict

RULE_ID = "R14"
TITLE = "같은 이름의 핀 상수가 서로 다른 핀을 가리킴"
SEVERITY = Severity.CRITICAL
TIER = "차별"
NEEDS = ["firmware"]

#: 이름 끝에서 뗄 접미. **하나만 뗀다.**
#: `TFT_BL_PIN` → `TFT_BL`. 여기서 더 떼면 `TFT_BL` 과 `TFT` 가 뭉쳐서
#: 서로 다른 신호가 같은 이름으로 보인다 — 그러면 오탐이 된다.
NAME_SUFFIX = re.compile(r"_(PIN|GPIO|IO)$", re.I)

#: 이 이름들은 너무 흔해서 우연히 겹친다. 겹쳐도 결함이라고 보지 않는다.
GENERIC_NAMES = frozenset({"PIN", "GPIO", "IO", "LED", "OUT", "IN", "CS", "CLK", "DATA"})


def normalize(symbol: str) -> str:
    """`TFT_BL_PIN` → `TFT_BL`. 대소문자를 안 가린다."""
    return NAME_SUFFIX.sub("", symbol.strip()).upper()


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    firmware = ctx.firmware
    if firmware is None or not firmware.pins:
        return []

    # 정규화한 이름 → {핀 번호: (원래 상수 이름, 그 핀 사용)}
    by_name: "OrderedDict[str, OrderedDict[int, tuple[str, object]]]" = OrderedDict()
    for use in firmware.pins:
        if use.gpio is None:
            continue  # 번호를 모르면 두 이름이 같은 핀인지도 모른다
        for symbol in use.symbols:
            key = normalize(symbol)
            if not key or key in GENERIC_NAMES:
                continue
            by_name.setdefault(key, OrderedDict()).setdefault(use.gpio, (symbol, use))

    findings: list[Finding] = []
    for key, seats in by_name.items():
        if len(seats) < 2:
            continue  # 한 핀에만 앉아 있으면 모순이 아니다
        findings.append(_finding(ctx, key, seats))
    return findings


def _net_of(ctx: Context, name: str) -> str | None:
    """회로도에 이 이름의 네트가 있으면 그 이름 그대로. 없으면 None.

    **판정에 쓰지 않는다.** 어느 쪽이 맞는지 사용자에게 보여줄 근거로만 쓴다 —
    네트명과 코드 상수명이 같은 규칙으로 지어졌다고 단정할 수 없기 때문이다.
    """
    graph = getattr(ctx, "netlist", None)
    netlist = getattr(graph, "netlist", None)
    if netlist is None:
        return None
    for net in netlist.nets:
        if net and normalize(net.rsplit("/", 1)[-1]) == name:
            return net
    return None


def _finding(ctx: Context, key: str, seats) -> Finding:
    rows = []
    evidence: list[Evidence] = []
    for gpio, (symbol, use) in seats.items():
        where = use.definition or (use.calls[0] if use.calls else None)
        rows.append(f"{symbol:<16} = {gpio}")
        if where is not None:
            evidence.append(
                Evidence.firmware(
                    file=where.file, line=where.line, snippet=where.snippet, highlight=[symbol]
                )
            )

    pins = " · ".join(f"GPIO{g}" for g in seats)
    lines = [f"코드가 {eul(key)} 두 핀으로 부릅니다", *rows]

    net = _net_of(ctx, key)
    if net:
        lines.append(f"회로도에는 이 이름의 네트가 있습니다 — {net}")
    evidence.insert(0, Evidence.netlist("\n".join(lines), [key, *pins.split(" · ")]))

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.FAIL,
        net=net,
        claim=(
            f"코드가 같은 이름({key})을 서로 다른 핀에 붙였습니다 — {pins}. "
            "배선이 바뀔 때 한쪽만 고치면 이렇게 됩니다. "
            "둘 중 하나는 지금 엉뚱한 핀을 건드리고 있습니다."
        ),
        evidence=tuple(evidence),
        suggestion=(
            f"{i_ga(key)} 실제로 어느 핀인지 회로도에서 확인하고 한쪽으로 맞추세요. "
            "정의가 여러 파일에 흩어져 있으면 한 파일로 모으는 편이 안전합니다."
        ),
        unresolved_reason=None,
    )
