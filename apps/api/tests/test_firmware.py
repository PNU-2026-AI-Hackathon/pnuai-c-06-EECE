"""펌웨어 정적 분석기 — 상수 추적 · 방향 판정 · 근거 위치."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from prefab.firmware import (
    DIRECTION_INPUT,
    DIRECTION_OUTPUT,
    DIRECTION_UNKNOWN,
    analyze,
    load_directory,
    load_zip,
    strip_noise,
)

FIRMWARE_DIR = (
    Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.firmware"
)


def _fw():
    return analyze(load_directory(FIRMWARE_DIR))


def test_real_firmware_uses_exactly_three_pins():
    """EXPECTED.md 2절의 표 그대로."""
    fw = _fw()
    assert {p.label for p in fw.pins} == {"D2", "D3", "D10"}
    assert fw.files == ("smart_shoe_cabinet_v1.ino",)


def test_directions_come_from_pinmode():
    fw = _fw()
    assert fw.find(silk="D2").direction == DIRECTION_OUTPUT
    assert fw.find(silk="D3").direction == DIRECTION_INPUT
    assert fw.find(silk="D10").direction == DIRECTION_OUTPUT


def test_constants_are_followed_to_the_pin():
    fw = _fw()
    assert fw.find(silk="D3").symbols == ("ECHO_PIN",)
    assert fw.find(silk="D2").symbols == ("TRIG_PIN",)


def test_evidence_points_at_a_real_line():
    fw = _fw()
    call = fw.find(silk="D3").first_call(prefer="pinMode")
    source = (FIRMWARE_DIR / call.file).read_text(encoding="utf-8").splitlines()
    assert source[call.line - 1].strip() == call.snippet
    assert "ECHO_PIN" in call.snippet


def test_file_path_is_relative_to_the_upload_root():
    """서버 임시 경로가 화면에 새면 안 된다 (요청서 2-2)."""
    fw = _fw()
    for p in fw.pins:
        for c in p.calls:
            assert not c.file.startswith("/")
            assert ":" not in c.file
            assert "tmp" not in c.file


def test_nothing_is_left_unresolved_in_the_fixture():
    assert _fw().unresolved == ()


def test_comments_and_strings_are_ignored():
    src = {
        "a.ino": (
            '// pinMode(D9, OUTPUT);\n'
            '/* digitalWrite(D8, HIGH); */\n'
            'Serial.println("pinMode(D7, OUTPUT)");\n'
            'void setup() { pinMode(D6, OUTPUT); }\n'
        )
    }
    fw = analyze(src)
    assert {p.label for p in fw.pins} == {"D6"}


def test_strip_noise_preserves_line_numbers():
    src = "a\n// 주석\n/* 여러\n줄 */\nb\n"
    assert len(strip_noise(src).splitlines()) == len(src.splitlines())


def test_define_and_numeric_pins():
    src = {"a.ino": "#define LED_PIN 18\nvoid setup(){ pinMode(LED_PIN, OUTPUT); }\n"}
    fw = analyze(src)
    pin = fw.find(gpio=18)
    assert pin is not None
    assert pin.gpio == 18 and pin.silk is None
    assert pin.direction == DIRECTION_OUTPUT


def test_gpio_num_macro():
    src = {"a.ino": "void setup(){ pinMode(GPIO_NUM_21, INPUT); }\n"}
    assert analyze(src).find(gpio=21).direction == DIRECTION_INPUT


def test_expression_that_cannot_be_resolved_is_recorded_not_guessed():
    """모르면 모른다고 한다 (CLAUDE.md 2-2). 조용히 버리지 않는다."""
    src = {"a.ino": "void loop(){ digitalWrite(pins[i], HIGH); }\n"}
    fw = analyze(src)
    assert fw.pins == ()
    assert len(fw.unresolved) == 1
    assert fw.unresolved[0].function == "digitalWrite"


def test_read_functions_imply_input():
    src = {"a.ino": "void loop(){ int v = analogRead(D4); }\n"}
    assert analyze(src).find(silk="D4").direction == DIRECTION_INPUT


def test_pinmode_wins_over_call_inference():
    """pinMode 로 선언한 방향이 더 강한 근거다."""
    src = {"a.ino": "void setup(){ pinMode(D5, OUTPUT); }\nvoid loop(){ digitalRead(D5); }\n"}
    assert analyze(src).find(silk="D5").direction == DIRECTION_OUTPUT


def test_unknown_direction_when_nothing_says_so():
    src = {"a.ino": "void setup(){ attachInterrupt(digitalPinToInterrupt(D1), f, RISING); }\n"}
    pin = analyze(src).find(silk="D1")
    assert pin is not None
    assert pin.direction in (DIRECTION_INPUT, DIRECTION_UNKNOWN)


def test_load_zip_reads_only_source_files():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("proj/main.ino", "void setup(){ pinMode(D2, OUTPUT); }")
        zf.writestr("proj/README.md", "설명")
        zf.writestr("__MACOSX/proj/._main.ino", "쓰레기")
        zf.writestr("proj/config.h", "#define LED 18")
    sources = load_zip(buf.getvalue())
    assert sorted(sources) == ["proj/config.h", "proj/main.ino"]


def test_analysis_is_a_pure_function():
    sources = load_directory(FIRMWARE_DIR)
    first = analyze(sources)
    second = analyze(sources)
    assert [(p.label, p.direction, len(p.calls)) for p in first.pins] == [
        (p.label, p.direction, len(p.calls)) for p in second.pins
    ]
