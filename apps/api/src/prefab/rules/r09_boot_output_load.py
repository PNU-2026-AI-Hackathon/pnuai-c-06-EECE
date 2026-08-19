"""R09 — 부팅 중 신호가 나오는 핀에 무언가 붙어 있다.

**칩 표(`docs/CHIPS.md`)가 어느 핀이 그런 핀인지 규정한다.**

```
ESP32     GPIO1  (U0TXD)   펌웨어가 돌기 전에 부팅 로그가 나온다
ESP32-C6  GPIO16 (U0TXD)   〃
```

이 핀들은 **펌웨어가 시작하기도 전에** 칩이 스스로 신호를 낸다. 부팅 로그가
115200 보드레이트로 그대로 나가므로, 여기 붙은 것은 매 부팅마다 움직인다.
릴레이면 딸깍거리고 모터 드라이버면 움찔한다.

## 왜 `정보` 인가

**이건 결함이 아니다.** 개발 보드는 거의 전부 TX 를 USB-UART 브리지나 디버그 헤더로
뽑아놓는다. 그게 정상이고, 그것까지 경고로 올리면 모든 보드에서 시끄러워진다.

그리고 넷리스트만으로는 **거기 붙은 게 브리지인지 릴레이인지 알 수 없다.**
부품을 모르면 판정하지 않는다 (CLAUDE.md 2-2). 우리가 아는 건 하나다 —
*이 핀은 부팅 중에 신호가 나온다.* 그 사실만 알려주고 판단은 사람이 한다.

BOM 이 들어와 부품이 식별되면 그때 좁힐 수 있다. 지금은 좁히는 척하지 않는다.
"""

from __future__ import annotations

from ..chips import Chip
from ..netlist.d356 import Netlist
from ..types import Context, Evidence, Finding, Severity, Verdict
from .r01_unusable_pin import chip_of

RULE_ID = "R09"
TITLE = "부팅 중 출력이 나오는 핀에 부하 연결"
SEVERITY = Severity.INFO
TIER = "기본"
NEEDS = ["netlist"]


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    graph = ctx.netlist
    pinmap = getattr(graph, "pinmap", None)
    chip = chip_of(pinmap, ctx.bom)
    if chip is None or not chip.boot_output or pinmap is None:
        return []  # 어느 칩인지 모르면 어느 핀이 부팅 중 출력인지도 모른다

    netlist: Netlist = graph.netlist
    signal_nets = set(graph.signal_nets())
    findings: list[Finding] = []

    for pad in pinmap.gpio_pads():
        if pad.gpio not in chip.boot_output:
            continue
        net = netlist.net_at(pad.ref, pad.pin, pad.x, pad.y)
        if netlist.is_dangling(net):
            continue  # 안 뽑아놓았으면 붙은 것도 없다
        if net not in signal_nets:
            continue  # 전원·접지에 물린 것은 이 규칙이 말할 것이 아니다

        others = [(ref, pin) for ref, pin in netlist.connections(net) if ref != pad.ref]
        if not others:
            continue  # 상대가 없으면 움직일 것도 없다

        findings.append(_finding(chip, pad, net, others))

    return findings


def _finding(chip: Chip, pad, net: str, others: "list[tuple[str, str]]") -> Finding:
    where = f"{pad.ref}.{pad.silk}" if pad.silk else f"{pad.ref}.{pad.pin}"
    token = f"GPIO{pad.gpio}"
    attached = ", ".join(f"{ref}.{pin}" for ref, pin in others[:6])

    lines = [
        f"{chip.name} — {token} 는 UART0 TX 다. 펌웨어 전에 부팅 로그가 나온다",
        f"{where} → {net}",
        f"같은 네트: {attached}",
    ]

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.FAIL,
        net=net,
        claim=(
            f"{where}({token}) 에 {attached} 가 붙어 있습니다. "
            f"{chip.name} 에서 이 핀은 펌웨어가 시작하기 전에 부팅 로그를 내보냅니다. "
            f"여기 붙은 것이 매 부팅마다 그 신호를 받습니다."
        ),
        evidence=(Evidence.netlist("\n".join(lines), [where, token]),),
        suggestion=(
            "붙은 것이 USB-UART 브리지나 디버그 헤더면 정상입니다. "
            "릴레이·모터 드라이버처럼 부팅 중에 움직이면 안 되는 것이라면 다른 핀으로 옮기세요. "
            "부품 목록(BOM)을 제출하면 무엇이 붙었는지까지 확인합니다."
        ),
        unresolved_reason=None,
    )
