"""R16 — 양성 / 음성 / 미해결.

**발견 루프가 찾아낸 첫 규칙이다.** 우리 규칙 13개가 이 모양을 하나도 안 보고 있었고,
모델이 우리 실측 보드 펌웨어에서 짚었다.

    R14  남의 보드 결함 → 규칙      (사람이 LLM 결과를 읽고 손으로 만들었다)
    R15  우리 보드 결함 → 규칙      (사람이 증상을 보고 만들었다)
    R16  **도구가 찾은 것 → 규칙**   (`discover/` 가 후보로 올렸다)
"""

from __future__ import annotations

from pathlib import Path

from prefab.firmware import analyze as analyze_firmware
from prefab.firmware import load_directory
from prefab.rules import r16_init_order_glitch as r16
from prefab.types import Context, Severity, Verdict

FIXTURES = Path(__file__).parent / "fixtures"


def _run(src: str):
    return r16.check(Context(firmware=analyze_firmware({"a.ino": src})))


# ── 양성 ────────────────────────────────────────────────────────────


def test_안전값이_HIGH_인데_나중에_쓰면_잡는다():
    found = _run(
        "#define RELAY_PIN D5\n"
        "void setup(){\n"
        "  pinMode(RELAY_PIN, OUTPUT);\n"
        "  digitalWrite(RELAY_PIN, HIGH);\n"
        "}\n"
    )
    assert len(found) == 1, found
    f = found[0]
    assert f.severity is Severity.WARNING
    assert f.verdict is Verdict.FAIL
    assert "HIGH" in f.claim and "LOW" in f.claim


def test_상수를_따라간다():
    """`RELAY_OFF` 는 코드가 `HIGH` 라고 밝혀 뒀다. 그걸 못 따라가면 규칙이 침묵한다."""
    found = _run(
        "#define RELAY_PIN D5\n"
        "const int RELAY_OFF = HIGH;\n"
        "void setup(){\n"
        "  pinMode(RELAY_PIN, OUTPUT);\n"
        "  digitalWrite(RELAY_PIN, RELAY_OFF);\n"
        "}\n"
    )
    assert len(found) == 1, found


def test_근거가_두_줄_다_실제_소스다():
    """사용자가 두 줄을 열어보고 순서를 확인할 수 있어야 한다."""
    f = _run(
        "#define P D5\nvoid setup(){\n  pinMode(P, OUTPUT);\n  digitalWrite(P, HIGH);\n}\n"
    )[0]
    lines = [e.line for e in f.evidence if e.kind == "firmware"]
    assert lines == [3, 4], lines
    assert all(e.snippet.strip() for e in f.evidence)


def test_고치는_법을_말한다():
    f = _run("#define P D5\nvoid setup(){\n  pinMode(P, OUTPUT);\n  digitalWrite(P, HIGH);\n}\n")[0]
    assert "순서를 바꾸세요" in f.suggestion


def test_실측_보드_v2_펌웨어에서_뜬다():
    """`RELAY_ON = LOW` 인 액티브 로우 구동이다. 모델이 짚은 바로 그 자리."""
    fw = analyze_firmware(load_directory(FIXTURES / "esp32-c6-presence-smart-light.v2.firmware"))
    found = r16.check(Context(firmware=fw))
    assert len(found) == 1, [f.claim for f in found]
    assert "D5" in found[0].claim


# ── 음성 ────────────────────────────────────────────────────────────


def test_순서를_바꾸면_조용하다():
    """**이게 고친 모양이다.** 래치에 값이 먼저 들어가고 pinMode 가 그걸 내보낸다."""
    assert _run(
        "#define P D5\nvoid setup(){\n  digitalWrite(P, HIGH);\n  pinMode(P, OUTPUT);\n}\n"
    ) == []


def test_안전값이_LOW_면_조용하다():
    """기본값과 같아서 창이 없다."""
    assert _run(
        "#define P D5\nvoid setup(){\n  pinMode(P, OUTPUT);\n  digitalWrite(P, LOW);\n}\n"
    ) == []


def test_쓰지_않으면_조용하다():
    """의도한 유휴 상태를 모른다. 모르면 판정하지 않는다."""
    assert _run("#define P D5\nvoid setup(){\n  pinMode(P, OUTPUT);\n}\n") == []


def test_입력_핀은_대상이_아니다():
    assert _run(
        "#define P D2\nvoid setup(){\n  pinMode(P, INPUT);\n}\n"
        "void loop(){ int x = digitalRead(P); }\n"
    ) == []


def test_REV2_펌웨어에서는_조용하다():
    """트랜지스터로 극성이 뒤집혀 `LOW` 가 OFF 다. 기본값과 같아서 창이 없다.

    **같은 순서인데 문제가 아니다** — 회로가 결정한다. 그래서 이 규칙은
    안전값을 코드에서 읽지, 순서만 보고 판정하지 않는다.
    """
    fw = analyze_firmware(load_directory(FIXTURES / "esp32-c6-presence-smart-light.rev2.firmware"))
    assert r16.check(Context(firmware=fw)) == []


# ── 미해결 ──────────────────────────────────────────────────────────


def test_안전값을_못_읽으면_판정하지_않는다():
    """`digitalWrite(pin, state)` 처럼 값을 확정 못 하면 조용하다 (헌법 2-2)."""
    assert _run(
        "#define P D5\nbool state;\n"
        "void setup(){\n  pinMode(P, OUTPUT);\n  digitalWrite(P, state);\n}\n"
    ) == []


def test_펌웨어가_없으면_아무_말도_하지_않는다():
    assert r16.check(Context()) == []


def test_loop_안의_쓰기는_안전값이_아니다():
    """**정상 케이스에서 오탐이 났던 자리다.**

    `loop()` 의 `digitalWrite(2, HIGH)` 는 초기 안전값이 아니라 평상시 동작이다.
    어디서 불렀는지가 뜻을 바꾼다 — 스코프를 안 보고 만들었다가 라벨 케이스
    `r01-ordinary-pin` 에서 경고가 떴다.
    """
    assert _run(
        "void setup(){\n  pinMode(2, OUTPUT);\n}\n"
        "void loop(){\n  digitalWrite(2, HIGH);\n}\n"
    ) == []


def test_스코프를_못_읽으면_판정하지_않는다():
    """함수 밖(전역 초기화 등)에서 부른 것은 순서를 말할 수 없다."""
    assert _run("#define P D5\npinMode(P, OUTPUT);\ndigitalWrite(P, HIGH);\n") == []
