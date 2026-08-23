"""칩을 모를 때 규칙이 **조용히 넘어가지 않는다.**

남의 보드 22개에서 규칙 5개(R01·R02·R03·R05·R09)가 통째로 죽어 있었는데,
화면에는 「규칙 14개 실행」 이라고 떴다. 사용자는 다 검사해서 깨끗한 줄 읽는다.
헌법 2-4 정면 위반이다 — 규칙을 못 돌렸는데 "이상 없음" 처럼 보이는 응답.
"""

from __future__ import annotations

from prefab import engine as engine_mod
from prefab.netlist.detect import parse_any
from prefab.netlist.graph import Graph
from prefab.runner import analyze

CHIP_RULES = ("R01", "R02", "R03", "R05", "R09")

FIRMWARE = {"main.cpp": "void setup() {\n  pinMode(8, OUTPUT);\n}\n"}


def _netlist(value: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<export version="E">
  <components><comp ref="U1"><value>{value}</value></comp></components>
  <nets>
    <net code="1" name="/GND"><node ref="U1" pin="1" pinfunction="GND"/></net>
    <net code="2" name="/SIG"><node ref="U1" pin="8" pinfunction="GPIO8"/></net>
  </nets>
</export>
"""


def test_칩을_모르면_실행했다고_세지_않는다():
    e = analyze(_netlist("ATTINY441-SSU"), filename="b.net.xml",
                firmware_sources=FIRMWARE).engine
    stuck = {s.rule for s in e.skipped_precondition}
    assert set(CHIP_RULES) <= stuck, f"칩 규칙이 그냥 실행됨으로 세어졌다: {e.ran}"
    for rule in CHIP_RULES:
        assert rule not in e.ran


def test_못_돌린_사유가_할_일을_말한다():
    e = analyze(_netlist("ATTINY441-SSU"), filename="b.net.xml",
                firmware_sources=FIRMWARE).engine
    detail = next(s.detail for s in e.skipped_precondition if s.rule == "R01")
    assert "부품번호" in detail          # 사용자가 할 수 있는 일
    assert "우리 표에" in detail          # 우리 쪽 한계도 같이 말한다


def test_칩을_알면_그대로_실행된다():
    e = analyze(_netlist("ESP32-C3"), filename="b.net.xml",
                firmware_sources=FIRMWARE).engine
    for rule in CHIP_RULES:
        assert rule in e.ran, f"{rule} 이 칩을 아는데도 안 돌았다"


def test_칸이_비어_있으면_그_칩_이름으로_말한다():
    """RP2040 은 스트래핑 핀이 **진짜로 없다.** 그것도 「판정 안 함」이다.

    조용히 통과시키면 "스트래핑 검사 통과" 로 읽힌다. 안 본 것과 봐서 괜찮은 것은 다르다.
    """
    e = analyze(_netlist("Pico"), filename="b.net.xml", firmware_sources=FIRMWARE).engine
    stuck = {s.rule: s.detail for s in e.skipped_precondition}
    assert "R03" in stuck and "RP2040" in stuck["R03"]
    assert "R01" not in stuck   # 입력 전용 핀은 「없다」가 판정 가능한 답이다


def test_실행과_건너뜀은_언제나_카탈로그_전체다():
    """계약 불변식. 새 건너뜀 사유가 생겨도 이건 안 깨져야 한다."""
    for value in ("ATTINY441-SSU", "ESP32-C3", "Pico", "10k 0.1%"):
        e = analyze(_netlist(value), filename="b.net.xml",
                    firmware_sources=FIRMWARE).engine
        assert len(e.ran) + len(e.skipped) == e.total, value


def test_blocked_없는_규칙은_그대로_돈다():
    """`blocked` 는 선택이다. 안 두면 엔진이 건드리지 않는다."""
    from prefab.rules import r17_pin_on_two_nets as r17
    assert not hasattr(r17, "blocked")
    ctx_engine = analyze(_netlist("Pico"), filename="b.net.xml",
                         firmware_sources=FIRMWARE).engine
    assert "R17" in ctx_engine.ran
