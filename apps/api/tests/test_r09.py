"""R09 — 부팅 중 출력이 나오는 핀에 부하 연결.

**칩 표(`docs/CHIPS.md`)가 진실이다.**

    ESP32     GPIO1  (U0TXD)
    ESP32-C6  GPIO16 (U0TXD)

**등급이 `정보` 인 것이 이 규칙의 핵심이다.** 개발 보드는 거의 전부 TX 를 뽑아놓고,
넷리스트만으로는 거기 붙은 게 USB-UART 브리지인지 릴레이인지 알 수 없다.
아는 사실 하나(이 핀은 부팅 중에 신호가 나온다)만 알리고 판단은 사람이 한다.
"""

from __future__ import annotations

from prefab.runner import analyze
from prefab.types import Severity
from tests._builder import board, rec

C6_BOM = b"Reference,MPN\nU1,ESP32-C6-WROOM-1\n"
ESP32_BOM = b"Reference,MPN\nU1,ESP32-D0WD-V3\n"


def _wire(*pairs: tuple[str, str]) -> str:
    """(패드, 상대부품) 목록으로 맨칩 보드를 만든다."""
    lines = []
    for i, (pin, peer) in enumerate(pairs):
        net = f"NET_{pin}"
        lines.append(rec(net, "U1", pin, x=0.1 * i))
        lines.append(rec(net, peer, "1", x=0.1 * i, y=0.5))
    return board(*lines)


def _run(netlist: str, *, bom: bytes | None = C6_BOM):
    a = analyze(netlist, bom_bytes=bom)
    return [f for f in a.engine.findings if f.rule == "R09"]


# ── 양성 ────────────────────────────────────────────────────────────


def test_TX_에_뭔가_붙으면_알린다():
    f = _run(_wire(("IO16", "K1"), ("IO2", "J1"), ("IO3", "J1"), ("IO17", "J1")))
    assert len(f) == 1
    assert f[0].severity is Severity.INFO  # 결함이 아니라 확인 요청이다
    assert "GPIO16" in f[0].claim
    assert "K1" in f[0].claim  # 무엇이 붙었는지 말해 준다


def test_칩이_다르면_다른_핀을_본다():
    """GPIO1 은 구형 ESP32 의 TX 이고 C6 에서는 아니다. 표대로 갈린다."""
    net = _wire(("IO1", "K1"), ("IO2", "J1"), ("IO3", "J1"), ("IO4", "J1"))
    assert len(_run(net, bom=ESP32_BOM)) == 1
    assert _run(net, bom=C6_BOM) == []


# ── 음성 ────────────────────────────────────────────────────────────


def test_TX_를_안_뽑으면_조용하다():
    assert _run(_wire(("IO2", "J1"), ("IO3", "J1"), ("IO17", "J1"), ("IO18", "J1"))) == []


def test_TX_가_미연결이면_조용하다():
    """뽑지 않은 핀에는 붙은 것도 없다."""
    lines = [rec("N/C", "U1", "IO16", x=0.9)]
    for i, p in enumerate(("IO2", "IO3", "IO17", "IO18")):
        lines.append(rec(f"NET_{p}", "U1", p, x=0.1 * i))
        lines.append(rec(f"NET_{p}", "J1", str(i + 1), x=0.1 * i, y=0.5))
    assert _run(board(*lines)) == []


# ── 미해결 ──────────────────────────────────────────────────────────


def test_칩을_모르면_아무_말도_안_한다():
    """어느 핀이 TX 인지는 칩마다 다르다. 추측하지 않는다."""
    net = _wire(("IO16", "K1"), ("IO2", "J1"), ("IO3", "J1"), ("IO17", "J1"))
    assert _run(net, bom=None) == []


# ── 불변식 ──────────────────────────────────────────────────────────


def test_정보도_요약에_세어진다():
    """INFO 를 안 세면 발견 수와 타일 합이 어긋난다. 심각도는 세 단계다."""
    from prefab.report import build_result

    netlist = _wire(("IO16", "K1"), ("IO2", "J1"), ("IO3", "J1"), ("IO17", "J1"))
    a = analyze(netlist, bom_bytes=C6_BOM)
    r = build_result(check_id="c", created_at="t", analysis=a, netlist_filename="b.d356")
    s = r["summary"]

    assert s["info"] >= 1
    assert s["critical"] + s["warning"] + s["info"] + s["cleared"] == len(r["findings"])
