"""R05 — 이 칩이 지원하지 않는 주변장치 조합.

**칩 표(`docs/CHIPS.md`)가 칩별로 규정한다.** 하나의 로직이 아니라 칩마다 다른 항목이다.

```
ESP32     ADC2 핀 + WiFi 동시            → CRITICAL
          (WiFi 가 ADC2 를 점유해서 읽기가 실패한다)
ESP32-C6  ADC2 없음                      → 해당 없음
          ADC1(GPIO0~6) ∩ 스트래핑(4·5)  → WARNING
```

R01 은 **핀 하나가 못 쓰는 핀인가**를 본다. 여기는 **두 기능을 같이 쓸 수 있는가**를 본다.
같은 핀이라도 조합에 따라 판정이 갈린다 — C6 의 GPIO4 는 아날로그로만 쓰면 경고이고,
디지털로만 쓰면 R01 의 스트래핑 경고다.

칩을 모르면 아무 말도 하지 않는다 (CLAUDE.md 2-2).
"""

from __future__ import annotations

from ..chips import Chip
from ..text import eul, eun
from ..types import Context, Evidence, Finding, Severity, Verdict
from .r01_unusable_pin import chip_of, gpio_of

RULE_ID = "R05"
TITLE = "이 칩이 지원하지 않는 주변장치 조합"
SEVERITY = Severity.CRITICAL
TIER = "차별"
NEEDS = ["netlist", "firmware"]

#: 아날로그 입력으로 읽는 함수. 이 호출이 있어야 ADC 를 쓴다고 본다.
ANALOG_READS = ("analogread", "analogreadmillivolts", "adc1_get_raw", "adc2_get_raw")


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    pinmap = getattr(ctx.netlist, "pinmap", None)
    chip = chip_of(ctx)
    if chip is None:
        return []

    firmware = ctx.firmware
    findings: list[Finding] = []

    for use in firmware.pins:
        gpio = gpio_of(use, pinmap)
        if gpio is None or not _reads_analog(use):
            continue

        if gpio in chip.adc2 and firmware.uses_wifi:
            findings.append(_finding(
                chip, gpio, use,
                Severity.CRITICAL,
                f"ADC2 채널이고 이 코드는 WiFi 를 씁니다",
                "WiFi 가 켜져 있는 동안 ADC2 는 쓸 수 없습니다. 읽기가 실패하거나 "
                "쓰레기 값이 나옵니다.",
                f"ADC1 채널({_span(chip.adc1)})로 옮기세요. WiFi 와 무관하게 동작합니다.",
            ))
            continue

        if gpio in chip.adc1 and gpio in chip.strapping:
            findings.append(_finding(
                chip, gpio, use,
                Severity.WARNING,
                "ADC 채널이면서 동시에 스트래핑 핀입니다",
                "부팅 시점에 이 핀에 걸린 아날로그 전압이 부팅 모드를 바꿀 수 있습니다. "
                "센서를 붙이면 전원을 넣을 때마다 부팅이 달라질 수 있습니다.",
                f"스트래핑이 아닌 ADC 채널로 옮기세요 — "
                f"{_span(tuple(g for g in chip.adc1 if g not in chip.strapping))}.",
            ))

    return findings


def _reads_analog(use) -> bool:
    return any(c.function.lower() in ANALOG_READS for c in use.calls)


def _span(gpios: tuple[int, ...]) -> str:
    return "GPIO " + ", ".join(str(g) for g in gpios) if gpios else "없음"


def _finding(
    chip: Chip, gpio: int, use, severity: Severity, what: str, why: str, fix: str
) -> Finding:
    where = f"{use.silk}(GPIO{gpio})" if use.silk else f"GPIO{gpio}"

    evidence: list[Evidence] = [
        Evidence.netlist(f"{chip.name} — {eun(where)} {what}", [where])
    ]
    for call in use.calls[:3]:
        evidence.append(Evidence.firmware(
            file=call.file, line=call.line, snippet=call.snippet, highlight=[use.token]
        ))

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=severity,
        verdict=Verdict.FAIL,
        net=None,
        claim=f"코드가 {eul(where)} 아날로그 입력으로 읽습니다. {chip.name} 에서 {what}. {why}",
        evidence=tuple(evidence),
        suggestion=fix,
        unresolved_reason=None,
    )


def blocked(ctx) -> str | None:
    """어느 칩인지 모르면 이 규칙은 **시작도 못 한다.**

    조용히 빈 목록을 돌려주면 화면에 "규칙 실행됨" 으로 세어져서, 사용자는 검사해서
    깨끗한 줄 안다. 실제로는 아무것도 안 본 것이다 (헌법 2-4).

    푸는 법은 사용자가 할 수 있는 일로 적는다 — 우리 표에 없는 칩이면 그것도 말한다.
    """
    if chip_of(ctx) is not None:
        return None
    return (
        "어느 칩인지 알아내지 못했습니다 — 부품번호(MPN)를 BOM 이나 회로도 심볼에 "
        "채우면 판정합니다. 채워져 있는데도 이 문구가 보이면 그 칩이 아직 우리 표에 "
        "없는 것입니다 (docs/CHIPS.md)."
    )
