"""R01 — 코드가 이 칩에서 쓸 수 없는 핀을 사용.

**칩 표(`docs/CHIPS.md`)가 이 규칙을 칩별로 규정한다.** 코드가 아니라 표가 진실이다.

```
ESP32     입력 전용 핀에 OUTPUT   → CRITICAL
ESP32-C6  플래시 핀 사용          → CRITICAL   (내장 플래시 전용, 쓰면 부팅 실패)
          스트래핑 핀 사용        → WARNING    (부팅 모드가 흔들릴 수 있다)
```

R02 는 같은 것을 **회로도 쪽에서** 본다. 여기는 **코드 쪽**이다 — 배선이 없어도
코드가 그 핀을 부르면 잡는다.

칩을 모르면 아무 말도 하지 않는다. 칩마다 못 쓰는 핀이 다른데 추측해서 경고하면
그게 오탐이다 (CLAUDE.md 2-2 · 2-3).
"""

from __future__ import annotations

from ..chips import CHIPS, MODULES, Chip
from ..mpn import known_mpns
from ..types import Context, Evidence, Finding, Severity, Verdict

RULE_ID = "R01"
TITLE = "코드가 이 칩에서 쓸 수 없는 핀을 사용"
SEVERITY = Severity.CRITICAL
TIER = "차별"
NEEDS = ["netlist", "firmware"]


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    pinmap = getattr(ctx.netlist, "pinmap", None)
    chip = chip_of(ctx)
    if chip is None:
        return []  # 어느 칩인지 모르면 못 쓰는 핀도 모른다

    findings: list[Finding] = []
    for use in ctx.firmware.pins:
        gpio = gpio_of(use, pinmap)
        if gpio is None:
            continue  # 실크를 GPIO 로 못 풀면 표와 대조할 수 없다
        verdict = _judge(chip, gpio, use)
        if verdict is not None:
            findings.append(_finding(chip, gpio, use, *verdict))
    return findings


def gpio_of(use, pinmap) -> int | None:
    """실크 라벨을 GPIO 번호로 푼다.

    펌웨어는 보드 실크(`D5`)를 부르고 칩 표는 GPIO 번호를 쓴다. 그 사이를 잇는 것이
    핀아웃 매칭이고, R07 도 같은 경로를 쓴다. 여기서 다른 경로를 쓰면 두 규칙이
    다른 핀을 가리키게 된다.
    """
    if use.gpio is not None:
        return use.gpio
    if pinmap is None or not use.silk:
        return None
    found = pinmap.find(silk=use.silk)
    return found.gpio if found else None


def chip_of(ctx) -> Chip | None:
    """어느 칩인지 정한다. 모듈 매칭이 먼저, 없으면 부품번호.

    모듈 보드는 핀아웃 매칭이 칩까지 말해 준다. **맨칩 설계는 그게 없어서**
    부품번호로 알아내야 한다 — 패드 이름은 GPIO 번호만 말해 주고, 그 번호가
    스트래핑인지 플래시인지는 칩마다 다르다.

    부품번호는 BOM 과 **회로도 둘 다**에서 온다 (`mpn.known_mpns`).
    회로도 넷리스트(kicadxml)는 심볼 필드에 부품번호를 실어 오므로,
    BOM 을 안 낸 사람의 보드에서도 칩이 정해진다.
    """
    graph = ctx.netlist
    pinmap = getattr(graph, "pinmap", None)
    if pinmap is not None:
        for module_id in getattr(pinmap, "modules_matched", {}).values():
            module = MODULES.get(module_id)
            if module is not None:
                return CHIPS.get(module.chip)

    netlist = getattr(graph, "netlist", None)
    if netlist is None:
        return None
    for mpn in known_mpns(netlist, ctx.bom):
        chip = _chip_from_mpn(mpn)
        if chip is not None:
            return chip
    return None


def _chip_from_mpn(mpn: str) -> Chip | None:
    """부품번호에서 칩을 알아본다. `ESP32-C6-WROOM-1` · `ESP32-C6` 둘 다 같은 칩이다.

    긴 id 부터 본다 — `esp32c6` 가 `esp32` 보다 먼저 걸려야 한다.
    """
    key = "".join(ch for ch in mpn.lower() if ch.isalnum())
    for chip_id in sorted(CHIPS, key=len, reverse=True):
        if chip_id in key:
            return CHIPS[chip_id]
    return None


def _judge(chip: Chip, gpio: int, use) -> tuple[Severity, str, str] | None:
    """(심각도, 무엇, 왜) 또는 None. 표에 없는 핀은 정상이다."""
    if gpio in chip.spi_flash:
        return (
            Severity.CRITICAL,
            "내장 플래시 전용 핀",
            "이 핀은 칩 내부 플래시가 쓴다. 코드가 가져다 쓰면 부팅이 실패한다.",
        )
    if gpio in chip.input_only:
        # 입력 전용 핀은 읽는 것까지는 정상이다. 출력으로 쓸 때만 문제다.
        if use.direction == "output":
            return (
                Severity.CRITICAL,
                "입력 전용 핀",
                "이 핀은 출력으로 설정할 수 없다. 내부 풀업·풀다운도 없다.",
            )
        return None
    if gpio in chip.strapping:
        return (
            Severity.WARNING,
            "스트래핑 핀",
            "부팅 시점의 레벨이 부팅 모드를 정한다. 코드가 이 핀을 구동하면 "
            "다음 부팅이 흔들릴 수 있다.",
        )
    return None


def _finding(chip: Chip, gpio: int, use, severity: Severity, what: str, why: str) -> Finding:
    where = f"{use.silk}(GPIO{gpio})" if use.silk else f"GPIO{gpio}"

    lines = [f"{chip.name} — {where} 는 {what}이다"]
    evidence: list[Evidence] = [Evidence.netlist("\n".join(lines), [where])]
    for call in use.calls[:3]:
        evidence.append(
            Evidence.firmware(
                file=call.file, line=call.line, snippet=call.snippet, highlight=[use.token]
            )
        )

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=severity,
        verdict=Verdict.FAIL,
        net=None,  # 핀 단위 발견이다. 네트가 없을 수도 있다
        claim=f"코드가 {where} 를 사용합니다. {chip.name} 에서 이 핀은 {what}입니다. {why}",
        evidence=tuple(evidence),
        suggestion=(
            f"다른 GPIO 로 옮기세요. {chip.name} 에서 쓸 수 없는 핀은 "
            f"`docs/CHIPS.md` 에 표로 있습니다."
        ),
        unresolved_reason=None,
    )
