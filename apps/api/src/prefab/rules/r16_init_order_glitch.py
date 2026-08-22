"""R16 — 안전값을 쓰기 전에 핀을 출력으로 바꿔 부팅마다 순간 구동된다.

**발견 루프가 찾아낸 첫 규칙이다.** 우리 규칙 13개가 이 모양을 하나도 안 보고 있었고,
모델이 우리 실측 보드 펌웨어에서 짚었다 (`discover/`).

## 무슨 일이 일어나나

    setup() {
      pinMode(RELAY_PIN, OUTPUT);            // ← 출력 래치 기본값(LOW)이 여기서 나간다
      digitalWrite(RELAY_PIN, RELAY_OFF);    // ← HIGH. 여기서야 안전해진다
    }

두 줄 사이에서 핀이 **LOW 로 구동된다.** `RELAY_OFF` 가 HIGH 라는 것은 코드가
스스로 밝힌 것이고, 그 말은 **LOW 가 켜짐**이라는 뜻이다. 즉 매 부팅·매 리셋마다
그 부하가 짧게 통전된다.

순서를 뒤집으면 사라진다 — `digitalWrite` 를 먼저 하면 래치에 값이 먼저 들어가고,
`pinMode(OUTPUT)` 이 그 값을 내보낸다.

## R09 와 다르다

R09 는 **칩이** 부팅 중 자동으로 내보내는 출력(스트래핑·부트 로그)을 본다.
R16 은 **코드가** 만드는 창이다. 칩 표가 없어도 성립하고, 회로도가 없어도 성립한다.

## 왜 회로도를 안 봐도 되나

이 판정에 필요한 것은 **코드가 스스로 밝힌 안전값**뿐이다. `digitalWrite` 로 먼저
쓰는 값이 그 핀의 의도된 유휴 상태이고, 그것이 HIGH 면 기본값 LOW 는 그 반대다.
무엇이 달려 있는지 몰라도 "의도한 것과 반대 레벨이 잠깐 나간다" 는 말은 성립한다.

## 왜 경고인가

**얼마나 나쁜지는 무엇이 달렸는지에 달렸다.** LED 면 눈에 안 보이고, 릴레이면
접점이 붙고, 모터면 튄다. 넷리스트를 봐도 그 부하가 그 펄스를 견디는지는 모른다.
치명으로 올리면 LED 하나 때문에 빨간불이 나고, 그러면 이 규칙이 제일 먼저 꺼진다
(헌법 2-3). **고치는 비용이 두 줄 순서를 바꾸는 것뿐**이라 경고로도 충분히 고쳐진다.

## 오탐을 막는 선

- **안전값을 못 읽으면 아무 말도 하지 않는다.** `digitalWrite(pin, someVar)` 처럼
  값을 확정 못 하면 판정하지 않는다 (헌법 2-2)
- **안전값이 LOW 면 조용하다.** 기본값과 같아서 창이 없다
- **`digitalWrite` 가 `pinMode` 보다 먼저면 조용하다.** 그게 고친 모양이다
- **`setup()` 에서 한 번도 안 쓰면 조용하다.** 의도한 유휴 상태를 모른다
"""

from __future__ import annotations

from ..text import eul
from ..types import Context, Evidence, Finding, Severity, Verdict

RULE_ID = "R16"
TITLE = "안전값을 쓰기 전에 출력으로 바꿔 부팅마다 순간 구동됨"
SEVERITY = Severity.WARNING
TIER = "차별"
NEEDS = ["firmware"]

#: 핀을 출력으로 바꾸는 호출
MODE_CALL = "pinMode"
#: 핀에 값을 쓰는 호출
WRITE_CALL = "digitalWrite"

#: **초기화 함수.** 여기 밖의 `digitalWrite` 는 안전값이 아니라 평상시 동작이다.
#:
#: 이걸 안 보고 만들었다가 정상 케이스에서 오탐이 났다 — `loop()` 안의
#: `digitalWrite(2, HIGH)` 를 "초기 안전값" 으로 읽었다. 어디서 불렀는지가 뜻을 바꾼다.
INIT_SCOPE = "setup"

#: `pinMode(pin, OUTPUT)` 직후 출력 래치가 내보내는 값.
#: Arduino 계열 코어는 출력 레지스터 기본값이 0 이다.
DEFAULT_LEVEL = "LOW"

#: 안전값으로 인정하는 표기. 이 밖의 것은 **모르는 것으로 다룬다.**
LEVELS = {"HIGH": "HIGH", "1": "HIGH", "LOW": "LOW", "0": "LOW"}


def check(ctx: Context) -> list[Finding]:
    """순수 함수. 네트워크·LLM·파일 IO·시간·난수 금지."""
    firmware = ctx.firmware
    if firmware is None or not firmware.pins:
        return []

    findings: list[Finding] = []
    for use in firmware.pins:
        mode = _first(use, MODE_CALL)
        write = _first(use, WRITE_CALL)
        if mode is None or write is None:
            continue  # 둘 다 있어야 순서를 말할 수 있다

        # 같은 파일 안에서만 순서를 본다. 파일이 다르면 실행 순서를 모른다
        if mode.file != write.file or write.line <= mode.line:
            continue

        level = _level(write, firmware.constants)
        if level is None or level == DEFAULT_LEVEL:
            continue  # 못 읽었거나, 기본값과 같아서 창이 없다

        findings.append(_finding(use, mode, write, level))
    return findings


def _first(use, function: str):
    """그 핀에 대한 **`setup()` 안의** 첫 `function` 호출. 없으면 None.

    스코프를 안 보면 `loop()` 의 평상시 쓰기를 초기 안전값으로 읽는다.
    스코프를 못 읽은 호출(`scope == ""`)도 안 쓴다 — 모르면 판정하지 않는다.
    """
    hits = [c for c in use.calls if c.function == function and c.scope == INIT_SCOPE]
    return min(hits, key=lambda c: (c.file, c.line)) if hits else None


def _level(call, constants: "dict[str, str]") -> str | None:
    """`digitalWrite(pin, X)` 의 X 를 HIGH/LOW 로 푼다. 못 풀면 None.

    상수를 따라간다 — `RELAY_OFF` 는 코드가 `HIGH` 라고 밝혀 뒀다.
    **표에 없는 이름은 모르는 것으로 둔다.** 지어내면 그 위의 판정이 통째로 거짓이 된다.
    """
    text = call.snippet
    if "(" not in text or ")" not in text:
        return None
    inside = text[text.index("(") + 1 : text.rindex(")")]
    parts = [p.strip() for p in inside.split(",")]
    if len(parts) != 2:
        return None

    token = parts[1]
    seen: set[str] = set()
    while token in constants and token not in seen:
        seen.add(token)
        token = constants[token].strip()
    return LEVELS.get(token.upper())


def _finding(use, mode, write, level: str) -> Finding:
    pin = use.silk or use.token
    symbol = use.symbols[0] if use.symbols else use.token

    evidence = [
        Evidence.firmware(
            file=mode.file, line=mode.line, snippet=mode.snippet, highlight=[MODE_CALL, symbol]
        ),
        Evidence.firmware(
            file=write.file, line=write.line, snippet=write.snippet,
            highlight=[WRITE_CALL, symbol],
        ),
    ]

    return Finding(
        rule=RULE_ID,
        title=TITLE,
        tier=TIER,
        severity=SEVERITY,
        verdict=Verdict.FAIL,
        net=None,
        claim=(
            f"코드가 {eul(pin)} 출력으로 바꾼 뒤에 안전값({level})을 씁니다. "
            f"그 사이에는 핀이 {DEFAULT_LEVEL} 로 구동되므로, "
            f"부팅하거나 리셋할 때마다 이 핀에 달린 것이 짧게 동작합니다."
        ),
        evidence=tuple(evidence),
        suggestion=(
            f"두 줄의 순서를 바꾸세요 — `{WRITE_CALL}` 을 먼저 하면 래치에 값이 먼저 "
            f"들어가고 `{MODE_CALL}(OUTPUT)` 이 그 값을 내보냅니다. "
            f"{eul(pin)} 아무것도 안 달려 있거나 순간 동작이 문제되지 않는 부하라면 "
            f"그대로 두셔도 됩니다."
        ),
        unresolved_reason=None,
    )
