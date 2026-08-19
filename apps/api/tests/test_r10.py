"""R10 — 회로도가 바뀐 뒤 코드가 안 따라옴 (드리프트).

R07·R08 이 각자 절반씩 말하는 것을 하나로 잇는다. **둘이 같은 사건인지는
이전 상태를 알아야 말할 수 있고**, 모르면 잇지 않는다.

이전 넷리스트는 `datasheet` 와 같은 **선택 입력**이다. 계약 어휘를 넓히지 않는다.
"""

from __future__ import annotations

from pathlib import Path

from prefab.runner import analyze
from prefab.types import Severity, Verdict

FIXTURES = Path(__file__).parent / "fixtures"
BEFORE = (FIXTURES / "esp32-c6-presence-smart-light.d356").read_text()
AFTER = (FIXTURES / "esp32-c6-presence-smart-light.moved-to-d4.d356").read_text()
FIRMWARE = FIXTURES / "esp32-c6-presence-smart-light.firmware"


def _sources() -> dict[str, str]:
    return {p.name: p.read_text() for p in FIRMWARE.iterdir() if p.suffix == ".ino"}


def _run(netlist: str, *, previous: str | None):
    a = analyze(netlist, firmware_sources=_sources(), previous_netlist_text=previous)
    return [f for f in a.engine.findings if f.rule == "R10"]


# ── 양성 ────────────────────────────────────────────────────────────


def test_핀이_옮겨가고_코드가_안_따라오면_치명이다():
    f = _run(AFTER, previous=BEFORE)
    assert len(f) == 1
    assert f[0].severity is Severity.CRITICAL
    assert f[0].verdict is Verdict.FAIL
    assert f[0].net == "PRESENCE_3V3"
    assert f[0].unresolved_reason is None


def test_어디서_어디로_옮겨갔는지_말한다():
    """"뭔가 바뀌었다"로는 부족하다. 사용자가 코드의 어느 줄을 고칠지 알아야 한다."""
    f = _run(AFTER, previous=BEFORE)[0]
    assert "D2" in f.claim and "D4" in f.claim

    netlist_ev = [e for e in f.evidence if e.kind == "netlist"][0]
    assert "이전" in netlist_ev.text and "지금" in netlist_ev.text

    # 코드 근거가 붙는다 — 어느 파일 몇 줄인지까지
    code = [e for e in f.evidence if e.kind == "firmware"]
    assert code and code[0].line is not None


# ── 음성 ────────────────────────────────────────────────────────────


def test_이전_넷리스트가_없으면_아무_말도_안_한다():
    """지금 한 장만 보면 두 발견이 같은 사건인지 모른다. 추측하지 않는다."""
    assert _run(AFTER, previous=None) == []


def test_회로도가_안_바뀌었으면_조용하다():
    assert _run(BEFORE, previous=BEFORE) == []


def test_코드도_같이_옮겨갔으면_조용하다():
    """정상적으로 끝난 변경이다. 드리프트가 아니다."""
    moved_code = {"main.ino": "void setup(){ pinMode(D4, INPUT); }\nvoid loop(){}\n"}
    a = analyze(AFTER, firmware_sources=moved_code, previous_netlist_text=BEFORE)
    assert [f for f in a.engine.findings if f.rule == "R10"] == []


def test_펌웨어가_없으면_조용하다():
    """코드가 따라왔는지 안 왔는지 알 수 없다. NEEDS 가 firmware 를 요구한다."""
    a = analyze(AFTER, previous_netlist_text=BEFORE)
    assert [f for f in a.engine.findings if f.rule == "R10"] == []
