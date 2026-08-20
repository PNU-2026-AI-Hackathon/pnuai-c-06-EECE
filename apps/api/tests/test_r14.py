"""R14 — 양성 / 음성 / 미해결.

**이 규칙은 합성 케이스가 아니라 실제 보드에서 나왔다.**
`FForzano/xgsail-e1` (Apache-2.0) 에서 배선이 바뀌며 `User_Setup.h` 는 고쳐지고
`config.h` 는 안 따라온 자리를 LLM 이 먼저 찾았고, 그 패턴을 규칙으로 옮긴 것이다.
합성 케이스만 보던 동안에는 이런 모양이 있는 줄도 몰랐다 (`_docs/규모_실험.md`).
"""

from __future__ import annotations

from prefab.firmware import analyze as analyze_firmware
from prefab.rules import r14_pin_name_conflict as r14
from prefab.rules.r14_pin_name_conflict import normalize
from prefab.types import Context, Severity, Verdict


def _run(sources: "dict[str, str]"):
    return r14.check(Context(firmware=analyze_firmware(sources)))


# ── 양성 ────────────────────────────────────────────────────────────


def test_positive_same_name_on_two_pins():
    """실측 보드에서 나온 모양 그대로 — 접미가 붙은 쪽과 안 붙은 쪽."""
    findings = _run({
        "User_Setup.h": "#define TFT_BL 19\nvoid a(){ pinMode(TFT_BL, OUTPUT); }",
        "config.h": "#define TFT_BL_PIN 25\nvoid b(){ pinMode(TFT_BL_PIN, OUTPUT); }",
    })
    assert len(findings) == 1
    f = findings[0]
    assert f.severity is Severity.CRITICAL
    assert f.verdict is Verdict.FAIL
    assert "TFT_BL" in f.claim
    assert "GPIO19" in f.claim and "GPIO25" in f.claim


def test_positive_evidence_quotes_both_definitions():
    """양쪽 정의 줄을 **그대로** 인용한다. 사용자가 두 파일을 열어본다."""
    findings = _run({
        "a.h": "#define MOTOR_PIN 12\nvoid a(){ pinMode(MOTOR_PIN, OUTPUT); }",
        "b.h": "#define MOTOR 27\nvoid b(){ pinMode(MOTOR, OUTPUT); }",
    })
    files = {e.file for e in findings[0].evidence if e.kind == "firmware"}
    assert files == {"a.h", "b.h"}
    assert all(e.line is not None for e in findings[0].evidence if e.kind == "firmware")


# ── 음성 ────────────────────────────────────────────────────────────


def test_negative_same_name_same_pin_is_fine():
    """같은 핀을 두 이름으로 부르는 것은 정상이다. 경고하면 오탐 생성기가 된다."""
    assert _run({
        "a.h": "#define LED_STATUS_PIN 2\nvoid a(){ pinMode(LED_STATUS_PIN, OUTPUT); }",
        "b.h": "#define LED_STATUS 2\nvoid b(){ digitalWrite(LED_STATUS, HIGH); }",
    }) == []


def test_negative_different_names_are_different_signals():
    """`TFT_BL` 과 `TFT_BLK` 는 다른 이름이다. 접미를 더 떼면 이 둘이 뭉친다."""
    assert _run({
        "a.h": "#define TFT_BL 19\nvoid a(){ pinMode(TFT_BL, OUTPUT); }",
        "b.h": "#define TFT_BLK 25\nvoid b(){ pinMode(TFT_BLK, OUTPUT); }",
    }) == []


def test_negative_generic_names_are_ignored():
    """`LED` 같은 흔한 이름은 우연히 겹친다. 겹쳐도 결함으로 보지 않는다."""
    assert _run({
        "a.h": "#define LED 2\nvoid a(){ pinMode(LED, OUTPUT); }",
        "b.h": "#define LED_PIN 4\nvoid b(){ pinMode(LED_PIN, OUTPUT); }",
    }) == []


def test_negative_real_board_firmware_is_silent():
    """우리 실측 보드 펌웨어에는 이 결함이 없다. 뜨면 오탐이다."""
    from pathlib import Path

    from prefab.firmware import load_directory

    fixtures = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.firmware"
    assert r14.check(Context(firmware=analyze_firmware(load_directory(fixtures)))) == []


# ── 미해결 ──────────────────────────────────────────────────────────


def test_unresolved_no_firmware_says_nothing():
    """펌웨어가 없으면 볼 것이 없다. 엔진이 `skipped` 로 표시한다."""
    assert r14.check(Context()) == []


def test_unresolved_pin_number_unknown_is_skipped():
    """번호를 못 읽으면 두 이름이 같은 핀인지도 모른다. 추측해서 경고하지 않는다."""
    assert _run({
        "a.h": "void a(){ pinMode(SOME_UNRESOLVED, OUTPUT); }",
        "b.h": "void b(){ pinMode(SOME_UNRESOLVED_PIN, OUTPUT); }",
    }) == []


# ── 이름 정규화 ─────────────────────────────────────────────────────


def test_normalize_strips_one_suffix_only():
    assert normalize("TFT_BL_PIN") == "TFT_BL"
    assert normalize("TFT_BL") == "TFT_BL"
    assert normalize("tft_bl_pin") == "TFT_BL"
    # 두 번 떼면 `TFT_BL` 과 `TFT` 가 뭉친다 — 그러면 서로 다른 신호가 같아 보인다
    assert normalize("TFT_BL_PIN_PIN") == "TFT_BL_PIN"
