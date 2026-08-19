"""R09 — 부팅 시 출력 나오는 핀에 부하 연결.

**칩 표(`docs/CHIPS.md`)가 진실이다.**

    ESP32     GPIO0 · 1 · 3 · 5 · 14 · 15
    ESP32-C6  GPIO16 (U0TXD — 부팅 로그가 115200bps 로 나간다)

**직결된 구동 부품만 잡는다.** 커넥터로 빼는 것은 시리얼 콘솔이라 정상 설계이고,
그것까지 잡으면 거의 모든 개발보드에서 오탐이 난다 — 이 파일의 음성 케이스가
그 경계를 고정한다.
"""

from __future__ import annotations

from prefab.runner import analyze
from prefab.types import Severity, Verdict
from tests._builder import board, rec

C6_BOM = b"Reference,MPN\nU1,ESP32-C6-WROOM-1\n"
ESP32_BOM = b"Reference,MPN\nU1,ESP32-D0WD-V3\n"
RELAY_BOM = b"Reference,MPN\nU1,ESP32-C6-WROOM-1\nK1,JQC-3FF-S-Z\n"

#: C6 의 부팅 로그 핀(U0TXD)
BOOT_TX = "IO16"

#: 평범한 핀. 맨칩으로 인정받으려면 IO 패드가 최소 4개 있어야 한다.
PLAIN = ("IO2", "IO3", "IO17")


def _rest(*pins: str) -> list[str]:
    """나머지 핀은 커넥터로 평범하게 뺀다."""
    lines = []
    for i, p in enumerate(pins):
        net = f"NET_{p}"
        lines.append(rec(net, "U1", p, x=0.1 * (i + 1)))
        lines.append(rec(net, "J1", str(i + 1), x=0.1 * (i + 1), y=0.5))
    return lines


def _driven_by(pin: str, ref: str, load_pin: str, *others: str) -> str:
    """한 핀을 구동 부품에 직결한다."""
    return board(
        rec("CTRL", "U1", pin, x=0.0),
        rec("CTRL", ref, load_pin, x=0.0, y=0.4),
        *_rest(*others),
    )


def _through_resistor(pin: str, ref: str, load_pin: str, *others: str) -> str:
    """핀 → 저항 → 부하. 패드는 부하가 아니라 중간 네트에 있다."""
    return board(
        rec("CTRL", "U1", pin, x=0.0),
        rec("CTRL", "R9", "1", x=0.0, y=0.4),
        rec("CTRL_B", "R9", "2", x=0.0, y=0.8),
        rec("CTRL_B", ref, load_pin, x=0.0, y=1.2),
        *_rest(*others),
    )


def _run(netlist: str, *, bom: bytes | None = RELAY_BOM):
    a = analyze(netlist, bom_bytes=bom)
    return [f for f in a.engine.findings if f.rule == "R09"]


# ── 양성 ────────────────────────────────────────────────────────────


def test_부팅_로그_핀이_릴레이를_몰면_경고다():
    f = _run(_driven_by(BOOT_TX, "K1", "IN", *PLAIN))
    assert len(f) == 1
    assert f[0].severity is Severity.WARNING
    assert f[0].verdict is Verdict.FAIL
    assert "GPIO16" in f[0].claim
    assert "릴레이" in f[0].claim
    # 왜 펌웨어로 못 막는지가 문구에 있어야 한다. 그게 이 규칙의 요지다.
    assert "코드가 돌기 전" in f[0].claim
    assert f[0].unresolved_reason is None


def test_부팅_로그_핀은_사유가_따로_붙는다():
    """로그는 수백 밀리초 동안 계속 토글한다. HIGH 한 번과 다른 이야기다."""
    f = _run(_driven_by(BOOT_TX, "K1", "IN", *PLAIN))
    assert "부팅 로그" in f[0].claim and "115200" in f[0].claim


def test_칩이_다르면_다른_핀을_본다():
    """GPIO16 은 C6 의 U0TXD 이고 구형 ESP32 에서는 평범한 핀이다. 표대로 갈린다."""
    net = _driven_by(BOOT_TX, "K1", "IN", *PLAIN)
    assert len(_run(net, bom=RELAY_BOM)) == 1
    assert _run(net, bom=ESP32_BOM) == []


def test_트랜지스터도_부하로_센다():
    f = _run(_driven_by(BOOT_TX, "Q1", "G", *PLAIN))
    assert len(f) == 1
    assert "트랜지스터" in f[0].claim


# ── 음성 ────────────────────────────────────────────────────────────


def test_커넥터로_빼면_조용하다():
    """부팅 로그 핀을 헤더로 빼는 것이 시리얼 콘솔이다. 여기서 뜨면 오탐 폭탄이다."""
    assert _run(board(*_rest(BOOT_TX, *PLAIN))) == []


def test_부팅에_조용한_핀이_몰면_조용하다():
    assert _run(_driven_by("IO2", "K1", "IN", "IO3", BOOT_TX, "IO17")) == []


def test_저항을_거치면_조용하다():
    """직렬 저항은 완화책이다. 패드가 부하와 다른 네트에 있다."""
    assert _run(_through_resistor(BOOT_TX, "K1", "IN", *PLAIN)) == []


def test_수동_소자만_붙으면_조용하다():
    """풀다운 커패시터가 붙은 TX 핀은 정상이다."""
    assert _run(_driven_by(BOOT_TX, "C7", "1", *PLAIN)) == []


def test_안_뽑아놓은_핀은_정상이다():
    assert _run(board(rec("N/C", "U1", BOOT_TX, x=0.9), *_rest(*PLAIN, "IO7"))) == []


def test_레일에_직결된_것은_R03_영역이다():
    """같은 배선을 두 규칙이 두 번 읽히지 않는다."""
    net = board(
        rec("GND", "U1", BOOT_TX, x=0.0),
        rec("GND", "C1", "2", x=0.0, y=0.4),
        *_rest(*PLAIN),
    )
    assert _run(net) == []


def test_실측_보드에서는_아무_말도_안_한다():
    """XIAO 는 D6(GPIO16)을 안 뽑아놨다. 새 경고가 뜨면 골든이 깨진 것이다."""
    from pathlib import Path

    fixture = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"
    a = analyze(fixture.read_text(encoding="utf-8"), filename=fixture.name)
    assert [f for f in a.engine.findings if f.rule == "R09"] == []


# ── 미해결 ──────────────────────────────────────────────────────────


def test_칩을_모르면_아무_말도_안_한다():
    """어느 핀이 부팅 때 출력인지는 칩마다 다르다. 추측하지 않는다."""
    assert _run(_driven_by(BOOT_TX, "K1", "IN", *PLAIN), bom=None) == []


def test_부하의_부품번호가_없으면_사유를_남긴다():
    """판정은 그대로 두고, 무엇을 내면 확정되는지 적는다 (헌법 2-2)."""
    f = _run(_driven_by(BOOT_TX, "K1", "IN", *PLAIN), bom=C6_BOM)
    assert len(f) == 1
    assert f[0].verdict is Verdict.FAIL
    assert f[0].unresolved_reason is not None
    assert "K1" in f[0].unresolved_reason
