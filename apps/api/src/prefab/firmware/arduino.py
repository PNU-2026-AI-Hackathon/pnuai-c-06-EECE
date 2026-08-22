"""Arduino/C++ 소스에서 '코드가 어느 핀을 어떻게 쓰는지'만 뽑는다.

컴파일하지 않는다. 실행하지 않는다. LLM 을 부르지 않는다.
정규식으로 읽을 수 있는 것만 읽고, 못 읽은 것은 못 읽었다고 남긴다.

이 모듈은 **보드를 모른다.** `D2` 가 GPIO 몇 번인지는 모듈 핀아웃 표가 답한다.
여기서는 코드가 쓴 토큰과 방향, 그리고 근거 위치(파일:라인:발췌)까지만 확정한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------- 상수

#: 첫 번째 인자가 핀인 함수들. 값은 핀 인자의 위치(0-based).
PIN_ARGUMENT: dict[str, int] = {
    "pinMode": 0,
    "digitalWrite": 0,
    "digitalRead": 0,
    "analogRead": 0,
    "analogWrite": 0,
    "dacWrite": 0,
    "touchRead": 0,
    "pulseIn": 0,
    "pulseInLong": 0,
    "tone": 0,
    "noTone": 0,
    "ledcAttachPin": 0,
    "ledcAttach": 0,
    "adcAttachPin": 0,
    "digitalPinToInterrupt": 0,
}

#: 그 함수를 쓴다는 것 자체가 방향을 말해 주는 경우
#: `#include <WiFi.h>` 또는 `#include "x.h"`.
INCLUDE_PATTERN = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', re.M)

DIRECTION_BY_FUNCTION: dict[str, str] = {
    "digitalWrite": "output",
    "analogWrite": "output",
    "dacWrite": "output",
    "tone": "output",
    "noTone": "output",
    "ledcAttachPin": "output",
    "ledcAttach": "output",
    "digitalRead": "input",
    "analogRead": "input",
    "touchRead": "input",
    "pulseIn": "input",
    "pulseInLong": "input",
    "digitalPinToInterrupt": "input",
}

OUTPUT_MODES = {"OUTPUT", "OUTPUT_OPEN_DRAIN"}
INPUT_MODES = {"INPUT", "INPUT_PULLUP", "INPUT_PULLDOWN", "ANALOG"}

DIRECTION_OUTPUT = "output"
DIRECTION_INPUT = "input"
DIRECTION_UNKNOWN = "unknown"

#: 소스로 읽을 확장자
SOURCE_SUFFIXES = (".ino", ".pde", ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp")

_IDENT = r"[A-Za-z_]\w*"

_SILK_NUMBER = re.compile(r"^[A-Za-z]+(\d+)$")

#: 가로 공백만. `\s` 를 쓰면 주석이 지워진 빈 줄들을 건너뛰며 매치해서
#: 정의 위치가 엉뚱한 줄로 잡힌다 (실제로 TRIG_PIN 이 1번 줄로 잡혔다).
_H = r"[^\S\n]"

_DEFINE = re.compile(rf"^{_H}*#{_H}*define{_H}+({_IDENT}){_H}+([^\s/]+)", re.M)
_CONST = re.compile(
    rf"^{_H}*(?:static{_H}+)?(?:const|constexpr){_H}+\w+{_H}+"
    rf"({_IDENT}){_H}*={_H}*([^;\n]+);",
    re.M,
)
#: 함수 호출의 **시작**만 찾는다. 인자는 괄호 균형을 세어서 잘라낸다.
#: 정규식으로 `\(([^()]*)\)` 를 쓰면 `pinMode(lookup(), INPUT)` 처럼 인자 안에
#: 괄호가 있는 호출을 **통째로 못 본다.** 조용히 버리는 자리가 되므로 스캐너로 바꿨다.
_CALL_HEAD = re.compile(rf"\b({_IDENT})\s*\(")

_SILK = re.compile(r"^(D\d{1,2}|A\d{1,2})$")
_NUMBER = re.compile(r"^(\d{1,3})$")
_GPIO_NUM = re.compile(r"^GPIO_NUM_(\d{1,3})$")


# --------------------------------------------------------------------- 타입

#: 못 읽은 이유. 위치만 남기면 나중에 AI 를 어디에 붙일지 알 수 없다 (결정기록 D-1).
REASON_ARRAY_INDEX = "배열 인덱스"
REASON_EXPRESSION = "계산식"
REASON_UNKNOWN_SYMBOL = "정의를 못 찾은 상수"
REASON_FUNCTION_CALL = "함수 반환값"
REASON_MEMBER = "구조체·객체 멤버"
REASON_OTHER = "해석 불가"

_ARRAY = re.compile(r"^\w+\s*\[")
_CALLEXPR = re.compile(rf"^{_IDENT}\s*\(")
_MEMBER = re.compile(r"^\w+\s*(\.|->)")
_ARITH = re.compile(r"[+\-*/%<>|&^]")


def classify_unreadable(expression: str, known_symbols: "set[str]") -> str:
    """왜 못 읽었는지. AI 를 붙일 때 이 분류가 그대로 작업 목록이 된다."""
    e = expression.strip()
    if _ARRAY.match(e):
        return REASON_ARRAY_INDEX
    if _MEMBER.match(e):
        return REASON_MEMBER
    if _CALLEXPR.match(e):
        return REASON_FUNCTION_CALL
    if _ARITH.search(e):
        return REASON_EXPRESSION
    if re.fullmatch(_IDENT, e) and e not in known_symbols:
        return REASON_UNKNOWN_SYMBOL
    return REASON_OTHER


@dataclass(frozen=True)
class PinCall:
    """코드에서 핀을 만진 자리 하나. 그대로 evidence 가 된다."""

    function: str
    file: str
    line: int
    snippet: str
    #: 이 호출이 들어 있는 **함수 이름** (`setup` · `loop` · …). 못 읽으면 빈 문자열.
    #:
    #: **어디서 불렀는지가 뜻을 바꾼다.** `digitalWrite(pin, HIGH)` 가 `setup()` 에
    #: 있으면 "이 핀의 안전한 초기값" 이고, `loop()` 에 있으면 그냥 평상시 동작이다.
    #: 이걸 안 보고 규칙을 만들었다가 정상 보드에서 오탐이 났다 (R16).
    scope: str = ""


@dataclass(frozen=True)
class Unreadable:
    """핀을 만지는 자리인데 **어느 핀인지 못 읽은** 곳.

    조용히 버리지 않는다. 위치와 사유를 함께 들고 다니면
    나중에 AI 추출을 붙일 때 **그 자리에만** 붙이면 된다 (결정기록 D-1).
    """

    expression: str
    reason: str
    call: PinCall

    @property
    def where(self) -> str:
        return f"{self.call.file}:{self.call.line}"

    def describe(self) -> str:
        return f"{self.where} — {self.expression} ({self.reason})"


@dataclass(frozen=True)
class PinUse:
    """코드가 쓰는 핀 하나."""

    #: 코드에 적힌 토큰. "D2" 또는 "21"
    token: str
    #: 보드 실크 라벨로 해석되면 그 이름. 숫자로 적었으면 None
    silk: str | None
    #: 칩 GPIO 번호로 해석되면 그 번호. 실크로 적었으면 None (핀맵이 채운다)
    gpio: int | None
    #: 이 핀을 가리킨 코드 상수 이름들 (TRIG_PIN 등)
    symbols: tuple[str, ...]
    direction: str
    calls: tuple[PinCall, ...]
    #: 상수가 선언된 자리. 없으면 코드가 핀을 직접 적었다는 뜻이다.
    definition: PinCall | None = None

    @property
    def sort_key(self) -> tuple:
        """D2 · D3 · D10 순서. 사전순으로 두면 D10 이 D2 앞에 온다."""
        if self.silk:
            m = _SILK_NUMBER.match(self.silk)
            return (0, self.silk[:1], int(m.group(1)) if m else 0)
        return (1, "", self.gpio if self.gpio is not None else 0)

    @property
    def label(self) -> str:
        return self.silk or (f"GPIO{self.gpio}" if self.gpio is not None else self.token)

    def first_call(self, prefer: str | None = None) -> PinCall:
        if prefer:
            for c in self.calls:
                if c.function == prefer:
                    return c
        return self.calls[0]


@dataclass(frozen=True)
class Firmware:
    """펌웨어 정적 분석 결과."""

    files: tuple[str, ...] = ()
    #: 읽은 소스의 총 줄 수. "무엇을 다 읽었는가"를 근거로 쓸 때 필요하다.
    total_lines: int = 0
    pins: tuple[PinUse, ...] = ()
    #: 상수까지 따라갔는데도 값을 확정 못 한 자리. 숨기지 않고 들고 다닌다.
    unresolved: tuple[Unreadable, ...] = ()
    #: 이름 → 값. `#define RELAY_OFF HIGH` 처럼 코드가 스스로 밝힌 것들.
    #:
    #: **규칙이 `digitalWrite(pin, RELAY_OFF)` 의 뜻을 알려면 이게 있어야 한다.**
    #: 여기 없는 이름은 규칙이 **모르는 것으로 다룬다** — 추측하지 않는다 (헌법 2-2).
    constants: "dict[str, str]" = field(default_factory=dict)
    #: `#include <X.h>` 로 끌어온 헤더 이름 (소문자, `.h` 없이).
    #: 칩이 지원하지 않는 **조합**을 보려면 어떤 주변장치를 쓰는지 알아야 한다 (R05).
    includes: tuple[str, ...] = ()

    @property
    def uses_wifi(self) -> bool:
        """WiFi 를 쓰는가. ESP32 구형에서 ADC2 와 동시에 못 쓴다.

        헤더 이름만 본다. `WiFi.begin()` 호출까지 따라가지 않는 이유는,
        헤더를 넣고 안 쓰는 코드보다 **쓰면서 헤더가 없는 코드가 없기** 때문이다.
        놓치는 쪽보다 넉넉히 잡는 쪽이 안전하다.
        """
        return any(h in ("wifi", "esp_wifi", "wifimulti", "wificlient") for h in self.includes)

    @property
    def unresolved_summary(self) -> str:
        """못 읽은 자리를 사유별로 묶어서 한 줄로."""
        if not self.unresolved:
            return ""
        counts: dict[str, int] = {}
        for u in self.unresolved:
            counts[u.reason] = counts.get(u.reason, 0) + 1
        return " · ".join(f"{reason} {n}곳" for reason, n in sorted(counts.items()))

    @property
    def labels(self) -> tuple[str, ...]:
        """코드가 쓰는 핀 이름을 사람이 읽는 순서로."""
        return tuple(p.label for p in sorted(self.pins, key=lambda p: p.sort_key))

    def find(self, *, silk: str | None = None, gpio: int | None = None) -> PinUse | None:
        """코드가 이 핀을 쓰는지. 실크로 적었든 번호로 적었든 같은 핀이면 찾아낸다."""
        for p in self.pins:
            if silk is not None and p.silk == silk:
                return p
        for p in self.pins:
            if gpio is not None and p.gpio == gpio:
                return p
        return None


# --------------------------------------------------------------------- 전처리

def strip_noise(source: str) -> str:
    """주석과 문자열을 공백으로 지운다. **줄 번호는 보존한다.**

    근거에 파일:라인을 붙여야 하므로 줄이 밀리면 안 된다.
    """
    out: list[str] = []
    i, n = 0, len(source)
    while i < n:
        c = source[i]
        two = source[i : i + 2]
        if two == "//":
            while i < n and source[i] != "\n":
                out.append(" ")
                i += 1
        elif two == "/*":
            while i < n and source[i : i + 2] != "*/":
                out.append("\n" if source[i] == "\n" else " ")
                i += 1
            out.append("  ")
            i += 2
        elif c in ('"', "'"):
            quote = c
            out.append(" ")
            i += 1
            while i < n and source[i] != quote:
                if source[i] == "\\":
                    out.append(" ")
                    i += 1
                if i < n:
                    out.append("\n" if source[i] == "\n" else " ")
                    i += 1
            out.append(" ")
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _classify(token: str) -> tuple[str | None, int | None]:
    """토큰을 (실크, gpio) 로 나눈다. 둘 다 None 이면 해석 못 한 것이다."""
    token = token.strip()
    if _SILK.match(token):
        return token, None
    m = _NUMBER.match(token)
    if m:
        return None, int(m.group(1))
    m = _GPIO_NUM.match(token)
    if m:
        return None, int(m.group(1))
    return None, None


def iter_calls(text: str):
    """(함수 이름, 인자 원문, 시작 위치). 중첩 호출도 안쪽까지 전부 나온다."""
    for m in _CALL_HEAD.finditer(text):
        depth, i, n = 1, m.end(), len(text)
        while i < n and depth:
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
            i += 1
        if depth == 0:
            yield m.group(1), text[m.end() : i - 1], m.start()


def _split_args(argtext: str) -> list[str]:
    """최상위 쉼표로만 자른다. `f(a, b), c` 를 세 조각으로 자르면 안 된다."""
    args, depth, current = [], 0, []
    for ch in argtext:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        args.append(tail)
    return args


def _scan_constants(
    cleaned: "dict[str, str]", sources: "dict[str, str]"
) -> "tuple[dict[str, str], dict[str, PinCall]]":
    """`#define` 과 `const int` 로 정의된 값 + **정의된 자리**.

    상수가 상수를 가리키면 따라간다. 정의 위치는 근거로 그대로 쓴다 —
    "이 핀이 어디서 D3 이 됐는지"를 사용자가 눌러서 확인할 수 있어야 한다.
    """
    raw: dict[str, str] = {}
    sites: dict[str, PinCall] = {}

    for path in sorted(cleaned):
        text = cleaned[path]
        original = sources[path].splitlines()
        for pattern in (_DEFINE, _CONST):
            for m in pattern.finditer(text):
                name = m.group(1)
                raw[name] = m.group(2).strip()
                line = text.count("\n", 0, m.start()) + 1
                sites[name] = PinCall(
                    function="정의",
                    file=path,
                    line=line,
                    snippet=original[line - 1].strip() if line <= len(original) else "",
                )

    resolved: dict[str, str] = {}
    for name in raw:
        seen: set[str] = set()
        value = name
        while value in raw and value not in seen:
            seen.add(value)
            value = raw[value]
        resolved[name] = value
    return resolved, sites


# --------------------------------------------------------------------- 본체

def analyze(sources: "dict[str, str]") -> Firmware:
    """{파일 상대경로: 소스 본문} → Firmware.

    파일 경로는 업로드한 zip 내부의 상대 경로 그대로다.
    서버 임시 디렉터리 경로가 섞이지 않는다 (계약 · 요청서 2-2).
    """
    cleaned = {path: strip_noise(text) for path, text in sources.items()}

    constants, definitions = _scan_constants(cleaned, sources)

    #: (silk, gpio) → 누적 정보
    buckets: dict[tuple[str | None, int | None], dict] = {}
    unresolved: list[Unreadable] = []

    for path in sorted(cleaned):
        text = cleaned[path]
        original = sources[path].splitlines()

        for function, argtext, start in iter_calls(text):
            if function not in PIN_ARGUMENT:
                continue
            args = _split_args(argtext)
            index = PIN_ARGUMENT[function]
            if len(args) <= index:
                continue

            expression = args[index]
            token = constants.get(expression, expression)
            silk, gpio = _classify(token)

            line = text.count("\n", 0, start) + 1
            snippet = original[line - 1].strip() if line <= len(original) else ""
            call = PinCall(
                function=function, file=path, line=line, snippet=snippet,
                scope=_scope_at(text, start),
            )

            if silk is None and gpio is None:
                unresolved.append(
                    Unreadable(
                        expression=expression,
                        reason=classify_unreadable(expression, set(constants)),
                        call=call,
                    )
                )
                continue

            bucket = buckets.setdefault(
                (silk, gpio),
                {
                    "token": token,
                    "symbols": [],
                    "direction": DIRECTION_UNKNOWN,
                    "calls": [],
                    "definition": None,
                },
            )
            if bucket["definition"] is None and expression in definitions:
                bucket["definition"] = definitions[expression]
            bucket["calls"].append(call)
            if expression != token and expression not in bucket["symbols"]:
                bucket["symbols"].append(expression)

            direction = DIRECTION_BY_FUNCTION.get(function)
            if function == "pinMode" and len(args) > 1:
                mode = args[1].strip()
                if mode in OUTPUT_MODES:
                    direction = DIRECTION_OUTPUT
                elif mode in INPUT_MODES:
                    direction = DIRECTION_INPUT
            # pinMode 로 선언한 방향이 더 강한 근거다. 먼저 정해진 것을 덮어쓰지 않는다.
            if direction and bucket["direction"] == DIRECTION_UNKNOWN:
                bucket["direction"] = direction

    pins = tuple(
        PinUse(
            token=b["token"],
            silk=silk,
            gpio=gpio,
            symbols=tuple(b["symbols"]),
            direction=b["direction"],
            calls=tuple(b["calls"]),
            definition=b["definition"],
        )
        for (silk, gpio), b in sorted(buckets.items(), key=lambda kv: str(kv[0]))
    )

    return Firmware(
        files=tuple(sorted(cleaned)),
        total_lines=sum(len(s.splitlines()) for s in sources.values()),
        pins=pins,
        unresolved=tuple(unresolved),
        constants=dict(constants),
        includes=_includes(sources.values()),
    )


#: 함수 정의의 머리. `void setup() {` · `static void loop(void) {`
_FUNCTION_HEAD = re.compile(r"^[A-Za-z_][\w \t\*&:<>,]*?\b(\w+)\s*\([^;{]*\)\s*\{", re.M)


def _scope_at(text: str, offset: int) -> str:
    """이 위치를 감싸는 함수 이름. 못 찾으면 빈 문자열.

    **정확한 파서가 아니다.** 그 위에서 가장 가까운 함수 머리를 고를 뿐이다.
    괄호를 세지 않으므로 중첩 정의에서는 틀릴 수 있는데, 아두이노 스케치에서는
    함수가 최상위에만 있어서 실무상 맞는다. **틀리면 규칙이 조용해질 뿐**이고
    (빈 문자열이면 `setup` 이 아니므로) 없는 발견을 만들지는 않는다.
    """
    last = ""
    for m in _FUNCTION_HEAD.finditer(text):
        if m.start() > offset:
            break
        last = m.group(1)
    return last


def _includes(sources) -> tuple[str, ...]:
    """`#include <WiFi.h>` · `#include "Adafruit_X.h"` 에서 헤더 이름을 뽑는다."""
    found: set[str] = set()
    for text in sources:
        for match in INCLUDE_PATTERN.finditer(text):
            name = match.group(1).rsplit("/", 1)[-1]
            found.add(name.removesuffix(".h").removesuffix(".hpp").lower())
    return tuple(sorted(found))
