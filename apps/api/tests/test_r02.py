"""R02 — 회로도가 SPI 플래시 전용 핀에 배선.

**칩 표(`docs/CHIPS.md`)가 진실이다.**

    ESP32     GPIO6 ~ GPIO11    내장 플래시 전용
    ESP32-C6  GPIO24 ~ GPIO30   내장 플래시 전용

R01 은 같은 핀을 코드 쪽에서 본다. 여기는 **회로도 쪽**이라 펌웨어가 없어도 돈다.

**우리 시연 보드(XIAO)는 여기 안 걸린다.** 헤더가 GPIO 0,1,2,16~23 만 뽑아서
플래시 핀(24~30)이 아예 없다. 그래서 케이스는 전부 맨칩 설계다.
"""

from __future__ import annotations

from prefab.runner import analyze
from prefab.types import Severity, Verdict
from tests._builder import board, rec

C6_BOM = b"Reference,MPN\nU1,ESP32-C6-WROOM-1\n"


def _bare(*pins: str) -> str:
    """맨칩 패드. 각 네트에 상대 패드를 붙인다 (패드 하나뿐이면 미연결이다)."""
    lines = []
    for i, p in enumerate(pins):
        net = f"NET_{p}"
        lines.append(rec(net, "U1", p, x=0.1 * i))
        lines.append(rec(net, "J1", str(i + 1), x=0.1 * i, y=0.5))
    return board(*lines)


def _run(netlist: str, *, bom: bytes | None = C6_BOM):
    a = analyze(netlist, bom_bytes=bom)
    return [f for f in a.engine.findings if f.rule == "R02"]


# ── 양성 ────────────────────────────────────────────────────────────


def test_플래시_핀이_배선되면_치명이다():
    f = _run(_bare("IO2", "IO3", "IO18", "IO24"))
    assert len(f) == 1
    assert f[0].severity is Severity.CRITICAL
    assert f[0].verdict is Verdict.FAIL
    assert "GPIO24" in f[0].claim
    assert f[0].unresolved_reason is None  # 배선 사실만으로 확정된다


def test_펌웨어가_없어도_돈다():
    """R01 과 다른 점이다. 코드를 안 줘도 배선만으로 판정한다."""
    assert len(_run(_bare("IO2", "IO3", "IO18", "IO25"))) == 1


# ── 음성 ────────────────────────────────────────────────────────────


def test_플래시_핀을_안_건드리면_조용하다():
    assert _run(_bare("IO2", "IO3", "IO18", "IO17")) == []


def test_안_뽑아놓은_플래시_핀은_정상이다():
    """미연결은 이 규칙의 대상이 아니다. 안 쓰는 게 맞는 동작이다."""
    lines = [rec("N/C", "U1", "IO24", x=0.9)]
    for i, p in enumerate(("IO2", "IO3", "IO18", "IO17")):
        lines.append(rec(f"NET_{p}", "U1", p, x=0.1 * i))
        lines.append(rec(f"NET_{p}", "J1", str(i + 1), x=0.1 * i, y=0.5))
    assert _run(board(*lines)) == []


def test_외부_플래시_IC_는_오탐이_아니다():
    """플래시 핀 여러 가닥이 한 IC 로 가면 그게 플래시다. 정상 설계다.

    이름으로는 못 가른다. 몇 가닥이 한 부품으로 모이는지로 본다.
    """
    lines = []
    for i, pin in enumerate(("IO24", "IO25", "IO26", "IO27")):
        net = f"FLASH_{pin}"
        lines.append(rec(net, "U1", pin, x=0.1 * i))
        lines.append(rec(net, "U9", str(i + 1), x=0.1 * i, y=0.6))
    assert _run(board(*lines)) == []


def test_플래시_IC_가_있어도_샌_가닥은_잡는다():
    """대부분은 U9 로 가는데 한 가닥만 커넥터로 빠지면 그건 오배선이다."""
    lines = []
    for i, pin in enumerate(("IO24", "IO25", "IO26", "IO27")):
        net = f"FLASH_{pin}"
        lines.append(rec(net, "U1", pin, x=0.1 * i))
        lines.append(rec(net, "U9", str(i + 1), x=0.1 * i, y=0.6))
    lines.append(rec("LED_NET", "U1", "IO28", x=0.9))
    lines.append(rec("LED_NET", "J1", "1", x=0.9, y=0.5))

    f = _run(board(*lines))
    assert len(f) == 1
    assert "GPIO28" in f[0].claim
    assert "U9" in f[0].claim  # 나머지가 어디로 가는지도 말해 준다


# ── 미해결 ──────────────────────────────────────────────────────────


def test_칩을_모르면_아무_말도_안_한다():
    """어느 핀이 플래시인지는 칩마다 다르다. 추측해서 경고하면 그게 오탐이다."""
    assert _run(_bare("IO2", "IO3", "IO18", "IO24"), bom=None) == []
