"""R03 — 스트래핑 핀이 전원·접지에 직결.

**칩 표(`docs/CHIPS.md`)가 진실이다.**

    ESP32     GPIO0 · 2 · 5 · 12 · 15
    ESP32-C6  GPIO4 · 5 · 8 · 9 · 15

**직결만 잡는다.** 저항·스위치를 거치면 패드는 다른 네트에 있으므로 안 걸린다.
풀업 저항과 부트 버튼은 정상 설계이고, 그것까지 잡으면 거의 모든 ESP32 보드에서
오탐이 난다 — 이 파일의 음성 케이스가 그 경계를 고정한다.
"""

from __future__ import annotations

from prefab.runner import analyze
from prefab.types import Severity, Verdict
from tests._builder import board, rec

C6_BOM = b"Reference,MPN\nU1,ESP32-C6-WROOM-1\n"
ESP32_BOM = b"Reference,MPN\nU1,ESP32-D0WD-V3\n"

#: 평범한 핀 넷. 맨칩으로 인정받으려면 IO 패드가 최소 4개 있어야 한다.
PLAIN = ("IO2", "IO3", "IO18")


def _rest(*pins: str) -> list[str]:
    lines = []
    for i, p in enumerate(pins):
        net = f"NET_{p}"
        lines.append(rec(net, "U1", p, x=0.1 * (i + 1)))
        lines.append(rec(net, "J1", str(i + 1), x=0.1 * (i + 1), y=0.5))
    return lines


def _tied(pin: str, rail: str, *others: str) -> str:
    """한 핀을 레일에 직결한다."""
    return board(
        rec(rail, "U1", pin, x=0.0),
        rec(rail, "C1", "2", x=0.0, y=0.4),
        *_rest(*others),
    )


def _through_resistor(pin: str, rail: str, *others: str) -> str:
    """핀 → 저항 → 레일. 패드는 레일이 아니라 중간 네트에 있다."""
    return board(
        rec("STRAP_PU", "U1", pin, x=0.0),
        rec("STRAP_PU", "R9", "1", x=0.0, y=0.4),
        rec(rail, "R9", "2", x=0.0, y=0.8),
        rec(rail, "C1", "2", x=0.1, y=0.8),
        *_rest(*others),
    )


def _run(netlist: str, *, bom: bytes | None = C6_BOM):
    a = analyze(netlist, bom_bytes=bom)
    return [f for f in a.engine.findings if f.rule == "R03"]


# ── 양성 ────────────────────────────────────────────────────────────


def test_접지에_직결되면_경고다():
    f = _run(_tied("IO8", "GND", *PLAIN))
    assert len(f) == 1
    assert f[0].severity is Severity.WARNING
    assert f[0].verdict is Verdict.FAIL
    assert "GPIO8" in f[0].claim
    assert "LOW" in f[0].claim
    assert f[0].unresolved_reason is None


def test_칩이_다르면_다른_핀을_본다():
    """GPIO12 는 구형 ESP32 스트래핑이고 C6 에서는 아니다. 표대로 갈린다."""
    net = _tied("IO12", "GND", *PLAIN)
    assert len(_run(net, bom=ESP32_BOM)) == 1
    assert _run(net, bom=C6_BOM) == []


# ── 음성 ────────────────────────────────────────────────────────────


def test_저항을_거치면_조용하다():
    """풀업은 정상 설계다. 여기서 경고가 뜨면 거의 모든 보드에서 오탐이 난다."""
    assert _run(_through_resistor("IO8", "3V3", *PLAIN)) == []


def test_스트래핑이_아닌_핀이_묶이면_조용하다():
    assert _run(_tied("IO18", "GND", "IO2", "IO3", "IO17")) == []


def test_평범한_신호에_붙으면_조용하다():
    """스트래핑 핀이라도 신호 네트에 붙은 것은 정상이다. 레벨이 고정되지 않는다."""
    assert _run(board(*_rest("IO8", "IO2", "IO3", "IO18"))) == []


def test_안_뽑아놓은_스트래핑_핀은_정상이다():
    assert _run(board(rec("N/C", "U1", "IO8", x=0.9), *_rest(*PLAIN, "IO17"))) == []


# ── 미해결 ──────────────────────────────────────────────────────────


def test_칩을_모르면_아무_말도_안_한다():
    """어느 핀이 스트래핑인지는 칩마다 다르다. 추측하지 않는다."""
    assert _run(_tied("IO8", "GND", *PLAIN), bom=None) == []
