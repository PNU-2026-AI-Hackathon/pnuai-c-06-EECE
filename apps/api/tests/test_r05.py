"""R05 — 이 칩이 지원하지 않는 주변장치 조합.

**칩 표가 칩별로 규정한다.** 하나의 로직이 아니다.

    ESP32     ADC2 핀 + WiFi 동시            → CRITICAL
    ESP32-C6  ADC2 없음                      → 해당 없음
              ADC1(GPIO0~6) ∩ 스트래핑(4·5)  → WARNING

R01 은 "핀 하나가 못 쓰는 핀인가", R05 는 "두 기능을 같이 쓸 수 있는가" 다.
"""

from __future__ import annotations

import pytest

from prefab.runner import analyze
from prefab.types import Severity
from tests._builder import board, rec

ESP32_BOM = b"Reference,MPN\nU1,ESP32-D0WD-V3\n"
C6_BOM = b"Reference,MPN\nU1,ESP32-C6-WROOM-1\n"


def _board(*pins: str) -> str:
    lines = []
    for i, p in enumerate(pins):
        net = f"NET_{p}"
        lines.append(rec(net, "U1", p, x=0.1 * i))
        lines.append(rec(net, "J1", str(i + 1), x=0.1 * i, y=0.5))
    return board(*lines)


BOARD = _board("IO4", "IO25", "IO32", "IO16")


def _run(code: str, *, bom: bytes = C6_BOM):
    a = analyze(BOARD, bom_bytes=bom, firmware_sources={"main.ino": code})
    return [f for f in a.engine.findings if f.rule == "R05"]


def _analog(gpio: int, *, wifi: bool = False) -> str:
    head = "#include <WiFi.h>\n" if wifi else ""
    return f"{head}void setup() {{}}\nvoid loop() {{ analogRead({gpio}); }}\n"


# ── ESP32 구형 — ADC2 + WiFi ─────────────────────────────────────────


def test_ADC2와_WiFi를_같이_쓰면_치명이다():
    f = _run(_analog(25, wifi=True), bom=ESP32_BOM)[0]
    assert f.severity is Severity.CRITICAL
    assert "WiFi" in f.claim


def test_ADC2라도_WiFi가_없으면_조용하다():
    """WiFi 를 안 쓰면 ADC2 는 정상이다. 핀만 보고 경고하면 오탐이다."""
    assert _run(_analog(25), bom=ESP32_BOM) == []


def test_WiFi를_써도_ADC1이면_조용하다():
    assert _run(_analog(32, wifi=True), bom=ESP32_BOM) == []


def test_대안_채널을_알려준다():
    f = _run(_analog(25, wifi=True), bom=ESP32_BOM)[0]
    assert "ADC1" in f.suggestion


# ── ESP32-C6 — ADC ∩ 스트래핑 ────────────────────────────────────────


def test_ADC이면서_스트래핑이면_경고다():
    f = _run(_analog(4))[0]
    assert f.severity is Severity.WARNING
    assert "부팅" in f.claim


def test_C6에는_ADC2가_없어서_WiFi_조합은_해당_없음():
    """C6 는 ADC2 자체가 없다. GPIO25 는 ADC 채널이 아니다."""
    assert _run(_analog(25, wifi=True)) == []


def test_겹치지_않는_ADC_채널은_조용하다():
    assert _run(_analog(2)) == []


def test_스트래핑이_아닌_채널을_알려준다():
    f = _run(_analog(4))[0]
    assert "GPIO" in f.suggestion and "4" not in f.suggestion.split("GPIO")[1][:12]


# ── 음성 · 미해결 ───────────────────────────────────────────────────


def test_디지털로만_쓰면_R05는_조용하다():
    """아날로그로 읽을 때만 ADC 조합 문제다. 디지털 사용은 R01 이 본다."""
    code = "void setup() { pinMode(4, OUTPUT); }\nvoid loop() { digitalWrite(4, HIGH); }\n"
    assert _run(code) == []


def test_칩을_모르면_아무_말도_안_한다():
    assert _run(_analog(4), bom=b"Reference,MPN\nU1,\n") == []


def test_펌웨어와_넷리스트가_둘_다_필요하다():
    """칩을 알아야 조합을 판정한다. 칩은 넷리스트나 BOM 에서 나온다."""
    from prefab.rules import r05_unsupported_combo as r05

    assert set(r05.NEEDS) == {"netlist", "firmware"}


def test_include가_없으면_WiFi를_쓴다고_보지_않는다():
    from prefab.firmware.arduino import analyze as parse_fw

    assert parse_fw({"a.ino": "void setup(){}"}).uses_wifi is False
    assert parse_fw({"a.ino": "#include <WiFi.h>\nvoid setup(){}"}).uses_wifi is True
