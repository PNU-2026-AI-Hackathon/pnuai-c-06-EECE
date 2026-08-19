"""R01 — 코드가 이 칩에서 쓸 수 없는 핀을 사용.

**칩 표(`docs/CHIPS.md`)가 진실이다.** 규칙은 표를 옮겨 적을 뿐이다.

    ESP32     입력 전용 핀에 OUTPUT   → CRITICAL
    ESP32-C6  플래시 핀 사용          → CRITICAL
              스트래핑 핀 사용        → WARNING

**우리 시연 보드(XIAO)는 여기 안 걸린다.** 헤더가 GPIO 0,1,2,16~23 만 뽑아서
스트래핑(4,5,8,9,15)도 플래시(24~30)도 없다. 그래서 이 파일의 케이스는 전부
맨칩 설계다 — 패드 이름이 곧 핀 이름인 경우.
"""

from __future__ import annotations

import pytest

from prefab.runner import analyze
from prefab.types import Severity
from tests._builder import board, rec

C6_BOM = b"Reference,MPN\nU1,ESP32-C6-WROOM-1\n"
ESP32_BOM = b"Reference,MPN\nU1,ESP32-D0WD-V3\n"


def _bare_board(*pins: str) -> str:
    """맨칩 패드. 최소 4개는 있어야 칩으로 인정한다 (커넥터 오인 방지).

    각 네트에 상대 패드를 붙인다 — 패드 하나뿐인 네트는 미연결이라 R07 이
    정당하게 뜬다. 여기서 재려는 건 R01 이지 R07 이 아니다.
    """
    lines = []
    for i, p in enumerate(pins):
        net = f"NET_{p}"
        lines.append(rec(net, "U1", p, x=0.1 * i))
        lines.append(rec(net, "J1", str(i + 1), x=0.1 * i, y=0.5))
    return board(*lines)


BOARD = _bare_board("IO2", "IO3", "IO7", "IO8", "IO24", "IO34")


def _run(code: str, *, bom: bytes = C6_BOM, netlist: str = BOARD):
    a = analyze(netlist, bom_bytes=bom, firmware_sources={"main.ino": code})
    return [f for f in a.engine.findings if f.rule == "R01"]


def _sketch(gpio: int, mode: str = "OUTPUT") -> str:
    return (
        f"const int PIN = {gpio};\n"
        f"void setup() {{ pinMode(PIN, {mode}); }}\n"
        f"void loop() {{ digitalWrite(PIN, HIGH); }}\n"
    )


# ── 양성 ────────────────────────────────────────────────────────────


def test_플래시_핀을_쓰면_치명이다():
    f = _run(_sketch(24))[0]
    assert f.severity is Severity.CRITICAL
    assert "부팅이 실패" in f.claim


def test_스트래핑_핀을_쓰면_경고다():
    """치명이 아니다. 의도적으로 쓰는 보드가 있다."""
    f = _run(_sketch(8))[0]
    assert f.severity is Severity.WARNING
    assert "부팅 모드" in f.claim


def test_근거에_코드_위치가_붙는다():
    """어느 줄에서 그 핀을 쓰는지 못 보여주면 고칠 수가 없다."""
    f = _run(_sketch(24))[0]
    kinds = [e.kind for e in f.evidence]
    assert "firmware" in kinds and "netlist" in kinds
    assert any(e.kind == "firmware" and e.line for e in f.evidence)


def test_입력_전용_핀에_출력을_주면_치명이다():
    """ESP32 구형 얘기다. C6 에는 입력 전용 핀이 없다."""
    f = _run(_sketch(34), bom=ESP32_BOM)[0]
    assert f.severity is Severity.CRITICAL
    assert "입력 전용" in f.claim


# ── 음성 ────────────────────────────────────────────────────────────


def test_표에_없는_핀은_조용하다():
    assert _run(_sketch(2)) == []


def test_입력_전용_핀을_읽기만_하면_정상이다():
    """읽는 건 된다. 출력으로 설정할 때만 문제다."""
    assert _run(_sketch(34, "INPUT"), bom=ESP32_BOM) == []


def test_같은_핀이_칩에_따라_다르게_판정된다():
    """GPIO8 은 C6 에서 스트래핑(경고)이고 구형 ESP32 에서는 플래시(치명)다.
    칩 표를 안 보고 하나로 판정하면 둘 중 하나는 틀린다."""
    assert _run(_sketch(8))[0].severity is Severity.WARNING
    assert _run(_sketch(8), bom=ESP32_BOM)[0].severity is Severity.CRITICAL


def test_표에_없는_핀은_칩이_달라도_조용하다():
    assert _run(_sketch(2)) == []
    assert _run(_sketch(3), bom=ESP32_BOM) == []


def test_회로도에_없는_핀도_코드가_부르면_잡는다():
    """R02 는 회로도 쪽, R01 은 코드 쪽이다. 배선이 없어도 코드가 부르면 문제다."""
    only_two = _bare_board("IO2", "IO3", "IO7", "IO9")
    assert _run(_sketch(24), netlist=only_two)


# ── 미해결 — 모르면 말하지 않는다 ────────────────────────────────────


def test_칩을_모르면_아무_말도_안_한다():
    """칩마다 못 쓰는 핀이 다르다. 추측해서 경고하면 그게 오탐이다 (헌법 2-2)."""
    assert _run(_sketch(24), bom=b"Reference,MPN\nU1,\n") == []


def test_BOM이_없으면_아무_말도_안_한다():
    a = analyze(BOARD, firmware_sources={"main.ino": _sketch(24)})
    assert [f for f in a.engine.findings if f.rule == "R01"] == []


def test_펌웨어가_없으면_엔진이_건너뛴다():
    from prefab.rules import r01_unusable_pin as r01

    assert "firmware" in r01.NEEDS


def test_IO_패드가_몇_개_안_되면_칩으로_안_본다():
    """커넥터에 `IO1` 하나 붙은 것을 칩으로 오인하면 그 뒤가 전부 오탐이다."""
    from prefab.netlist.d356 import parse_text
    from prefab.netlist import pinmap

    tiny = _bare_board("IO24", "IO8")
    assert len(pinmap.resolve(parse_text(tiny))) == 0
