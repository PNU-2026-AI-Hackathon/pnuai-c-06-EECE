"""R17 — 한 핀이 서로 다른 두 네트에 있음 (단락).

물리적으로 불가능한 배선이다. 핀 하나는 네트 하나에만 속한다.
두 네트에 있다면 그 두 네트가 그 핀에서 **붙어 있다**는 뜻이다.

## 어디서 왔나

**LLM 이 찾았고 코드가 확인했다.** 홀드아웃 보드 `EEPROM_programmer` 에서
Sonnet 이 "U3 15번 핀이 두 넷에 있다" 고 했고, 넷리스트를 열어 보니 사실이었다 —
`/D5` 에 `I/O5`, `/D7` 에 `I/O7` 로 같은 15번 핀이 두 번 나온다. EEPROM 의
데이터 선 두 개가 한 핀에 물린 것이다. 우리 규칙 14개 중 어느 것도 이 모양을
안 보고 있었다. R14 · R16 에 이어 **바깥에서 들어온 세 번째 규칙**이다.

## 핀 신원을 어떻게 잡나 — 이 규칙의 전부다

`(부품, 핀)` 만으로 보면 **우리 실측 보드에서 3건이 헛난다.** IPC-D-356 은 핀
이름을 4자로 자르기 때문에 서로 다른 핀이 같은 이름이 된다 (`U1` 의 D0·D1·D2 가
전부 `LP-G`, K1 의 패드 6개가 전부 `pad-`). 이름이 같다고 같은 핀이 아니다.

그래서 **좌표까지 넣어 물리 패드로 가른다.** 같은 실측 보드에서 0건이 된다.
회로도 넷리스트에는 좌표가 없지만 KiCad 의 핀 번호는 안 잘리므로 그것이 곧 신원이다.
좌표도 없고 이름도 잘린 형식이 들어오면 **아무 말도 하지 않는다** (헌법 2-2).
"""

from __future__ import annotations

from ..netlist.d356 import Netlist
from ..text import eun
from ..types import Context, Evidence, Finding, Severity, Verdict

RULE_ID = "R17"
TITLE = "한 핀이 서로 다른 두 네트에 연결됨"
SEVERITY = Severity.CRITICAL
TIER = "기본"
NEEDS = ["netlist"]


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    netlist: Netlist = ctx.netlist.netlist

    # **이름이 잘리는데 좌표까지 없으면 핀을 구분할 수 없다.** 그때는 안 본다.
    # 억지로 보면 잘린 이름이 같다는 이유로 멀쩡한 핀을 단락이라고 말하게 된다.
    if netlist.NAME_IS_WIDTH_LIMITED and not _has_coordinates(netlist):
        return []

    # 물리 패드 하나 → 그 패드가 나타난 네트들.
    where: dict[tuple, list[tuple[str, str | None]]] = {}
    for net, pads in netlist.nets.items():
        if netlist.is_dangling(net):
            continue  # 미연결 표시는 네트가 아니다
        for pad in pads:
            if pad.is_via:
                continue
            # **번호가 없으면 신원이 없다.** 심볼이 핀 번호를 안 붙이면 KiCad 는
            # `pin=""` 로 내보내고, 그러면 서로 다른 핀이 한 신원으로 뭉친다.
            #
            # 이 규칙의 첫 실전에서 바로 걸렸다 — `picoX7` 의 U2 에서 `GND` ·
            # `LINE_OUT_L` · `LINE_OUT_R` 세 핀이 전부 `pin=""` 이라 "한 핀이 3개
            # 네트에" 라는 오탐이 났다. 규칙이 처음 잡은 2건 중 1건이 이것이었다.
            #
            # 이름으로 대신 가를 수도 있지만 안 한다 — 이름이 잘리는 형식에서
            # 정확히 그 방식이 실측 보드에서 3건을 헛나게 했다. 모르면 모른다 (헌법 2-2).
            if not (pad.pin or "").strip():
                continue
            where.setdefault((pad.ref, pad.pin, pad.x, pad.y), []).append((net, pad.name))

    findings: list[Finding] = []
    for (ref, pin, _x, _y), rows in where.items():
        nets = sorted({net for net, _name in rows})
        if len(nets) < 2:
            continue
        findings.append(_finding(ref, pin, nets, rows))
    return findings


def _has_coordinates(netlist: Netlist) -> bool:
    """좌표가 실려 있는가. 하나라도 있으면 그 형식은 좌표를 싣는 형식이다."""
    return any(
        pad.x is not None
        for pads in netlist.nets.values()
        for pad in pads
        if not pad.is_via
    )


def _finding(ref: str, pin: str, nets: list[str], rows) -> Finding:
    # 심볼이 붙여둔 핀 이름이 서로 다르면 그 자체가 근거다 — `I/O5` 와 `I/O7` 이
    # 같은 15번 핀에 있다는 것은 심볼이나 배선이 잘못됐다는 뜻이다.
    names = sorted({name for _net, name in rows if name})
    lines = [f"{ref}.{pin}" + (f" ({name})" if name else "") + f" → {net}" for net, name in rows]

    label = f"{ref}.{pin}"
    detail = f" — 회로도에는 {' · '.join(names)} 로 적혀 있습니다" if len(names) > 1 else ""

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.FAIL,
        # 네트가 둘이라 하나를 못 고른다. 합치기(dedupe)는 네트 단위라 여기서는 안 돈다.
        net=None,
        claim=(
            f"{eun(label)} {len(nets)}개 네트에 동시에 연결되어 있습니다 "
            f"({' · '.join(nets)}){detail}. 핀 하나는 네트 하나에만 속하므로, "
            f"이 핀에서 두 네트가 붙어 있습니다."
        ),
        evidence=(Evidence.netlist("\n".join(lines), [label, *nets]),),
        suggestion=(
            f"{label} 에 연결된 배선을 확인하세요. 심볼에 같은 번호의 핀이 두 개 그려져 "
            f"있거나, 서로 다른 네트 라벨이 한 핀에 붙어 있습니다. 발주하면 그대로 단락됩니다."
        ),
        unresolved_reason=None,
    )
