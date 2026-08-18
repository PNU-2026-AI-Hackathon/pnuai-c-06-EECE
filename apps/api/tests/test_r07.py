"""R07 — 양성 / 음성 / 미해결."""

from __future__ import annotations

from pathlib import Path

from prefab.firmware import analyze as analyze_firmware
from prefab.firmware import load_directory
from prefab.netlist.d356 import parse, parse_text
from prefab.netlist.graph import Graph
from prefab.rules import r07_pin_not_connected as r07
from prefab.types import Context, Severity, Verdict

from _builder import board, rec

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE = FIXTURES / "esp32-c6-presence-smart-light.d356"
FIRMWARE_DIR = FIXTURES / "esp32-c6-presence-smart-light.firmware"

#: XIAO 헤더를 그대로 흉내 낸 합성 보드. 왼쪽 D0~D6, 오른쪽 5V·GND·3V3·D10~D7.
LEFT = ["LP-G", "LP-G", "LP-G", "SDIO", "SDIO", "SDIO", "GPIO"]
RIGHT = ["5V", "GND", "3V3", "D10_", "D9_M", "D8_S", "D7_R"]


def _synth_board(left_nets: "list[str]", right_nets: "list[str] | None" = None) -> str:
    """XIAO 헤더 + 이름 있는 네트마다 **상대편 패드 하나**.

    배선은 양 끝이 있어야 배선이다. U1 쪽 패드만 놓으면 그 네트는 패드가 하나뿐이라
    전기적으로는 미연결이고, 엔진도 그렇게 본다 (`Netlist.is_dangling`).
    실제 보드를 흉내내려면 상대가 있어야 한다.
    """
    right_nets = right_nets or ["N/C"] * 7
    lines = []
    for i, (pin, net) in enumerate(zip(LEFT, left_nets)):
        lines.append(rec(net, "U1", pin, x=-0.2635, y=0.7922 - 0.1 * i))
    for i, (pin, net) in enumerate(zip(RIGHT, right_nets)):
        lines.append(rec(net, "U1", pin, x=0.3365, y=0.7922 - 0.1 * i))

    # 이름 있는 네트마다 상대편을 하나씩. 부품마다 패드 1개라 열을 이루지 않아
    # 모듈 핀아웃 탐지(열 감지)를 방해하지 않는다.
    for i, net in enumerate(sorted({n for n in list(left_nets) + list(right_nets)
                                    if n and n != "N/C"})):
        lines.append(rec(net, f"X{i + 1}", "1", x=2.0 + 0.3 * i, y=0.0))
    return board(*lines)


def _run(netlist_text: str, sources: "dict[str, str]"):
    graph = Graph(parse_text(netlist_text))
    return r07.check(Context(netlist=graph, firmware=analyze_firmware(sources)))


def test_positive_real_board_two_findings():
    """EXPECTED.md 3절 — D3 와 D10 두 건. 그 이상도 이하도 아니다."""
    graph = Graph(parse(FIXTURE))
    firmware = analyze_firmware(load_directory(FIRMWARE_DIR))
    findings = r07.check(Context(netlist=graph, firmware=firmware))

    assert len(findings) == 2
    assert {f.claim.split("(")[0].split()[-1] for f in findings} == {"D3", "D10"}
    assert all(f.severity is Severity.CRITICAL for f in findings)


def test_positive_finding_is_final_without_a_bom():
    """데이터시트 0회로 확정된다. unresolved_reason 은 반드시 None (EXPECTED.md)."""
    graph = Graph(parse(FIXTURE))
    firmware = analyze_firmware(load_directory(FIRMWARE_DIR))
    for f in r07.check(Context(netlist=graph, firmware=firmware)):
        assert f.verdict is Verdict.FAIL
        assert f.unresolved_reason is None


def test_negative_pin_that_is_wired_produces_nothing():
    """D2 는 배선돼 있다. 코드가 써도 R07 은 조용하다."""
    text = _synth_board(["N/C", "N/C", "SENSE", "N/C", "N/C", "N/C", "N/C"])
    findings = _run(text, {"a.ino": "void setup(){ pinMode(D2, OUTPUT); }"})
    assert findings == []


def test_negative_unused_unconnected_pins_are_silent():
    """D0 · D1 · D4 · D6 는 미연결이지만 코드도 안 쓴다. 여기서 뜨면 오탐이다."""
    text = _synth_board(["N/C"] * 7)
    assert _run(text, {"a.ino": "void setup(){}"}) == []


def test_unresolved_pin_the_board_does_not_have_is_skipped():
    """코드가 D42 를 쓴다. 보드에 그런 핀이 없으면 판정하지 않는다."""
    text = _synth_board(["N/C"] * 7)
    assert _run(text, {"a.ino": "void setup(){ pinMode(D42, OUTPUT); }"}) == []


def test_unknown_module_produces_nothing():
    """핀아웃을 못 알아본 보드에서는 GPIO 번호를 모른다. 추측해서 판정하지 않는다."""
    text = board(rec("N/C", "U9", "AAAA", x=0.0, y=0.5), rec("SIG", "U9", "BBBB", x=0.0, y=0.4))
    assert _run(text, {"a.ino": "void setup(){ pinMode(D2, OUTPUT); }"}) == []


def test_evidence_has_both_lanes():
    """코드가 아는 것과 회로도가 아는 것이 한 카드에 같이 있어야 한다."""
    text = _synth_board(["N/C"] * 7)
    findings = _run(text, {"a.ino": "void setup(){ pinMode(D3, INPUT); }"})
    assert len(findings) == 1
    kinds = [e.kind for e in findings[0].evidence]
    assert "firmware" in kinds and "netlist" in kinds


def test_every_firmware_evidence_points_at_a_real_source_line():
    """발췌는 파일에 실제로 있는 줄이어야 한다. 없는 주석을 지어 붙이지 않는다."""
    graph = Graph(parse(FIXTURE))
    firmware = analyze_firmware(load_directory(FIRMWARE_DIR))
    source = (FIRMWARE_DIR / "smart_shoe_cabinet_v1.ino").read_text(encoding="utf-8").splitlines()

    for f in r07.check(Context(netlist=graph, firmware=firmware)):
        fw = [e for e in f.evidence if e.kind == "firmware"]
        assert len(fw) == 2  # 상수가 선언된 자리 + 그 핀을 실제로 만지는 자리
        for e in fw:
            assert e.line is not None
            assert source[e.line - 1].strip() == e.snippet


def test_constant_definition_is_one_of_the_anchors():
    """`const int ECHO_PIN = D3;` 이 어디서 왔는지 눌러서 확인할 수 있어야 한다."""
    graph = Graph(parse(FIXTURE))
    firmware = analyze_firmware(load_directory(FIRMWARE_DIR))
    d3 = next(
        f for f in r07.check(Context(netlist=graph, firmware=firmware)) if "D3" in f.claim
    )
    snippets = [e.snippet for e in d3.evidence if e.kind == "firmware"]
    assert any("const int ECHO_PIN = D3;" == s for s in snippets)
    assert any("pulseIn" in s for s in snippets)


def test_netlist_evidence_explains_the_name_collision():
    """SDIO 가 3개인데 왜 D3 인지 근거가 말해 줘야 한다."""
    graph = Graph(parse(FIXTURE))
    firmware = analyze_firmware(load_directory(FIRMWARE_DIR))
    d3 = next(
        f for f in r07.check(Context(netlist=graph, firmware=firmware)) if "D3" in f.claim
    )
    text = next(e for e in d3.evidence if e.kind == "netlist").text
    assert "패드명 SDIO" in text
    assert "3개" in text and "좌표로" in text


def test_direction_wording_follows_the_code():
    text = _synth_board(["N/C"] * 7)
    out = _run(text, {"a.ino": "void setup(){ pinMode(D3, INPUT); }"})[0]
    assert "입력으로 읽습니다" in out.claim
    inp = _run(text, {"a.ino": "void setup(){ pinMode(D3, OUTPUT); }"})[0]
    assert "출력으로 구동합니다" in inp.claim


def test_check_is_a_pure_function():
    graph = Graph(parse(FIXTURE))
    firmware = analyze_firmware(load_directory(FIRMWARE_DIR))
    ctx = Context(netlist=graph, firmware=firmware)
    assert [f.to_dict() for f in r07.check(ctx)] == [f.to_dict() for f in r07.check(ctx)]


# --------------------------------------------------------------- KiCad 방언
#
# kicad-cli 는 미연결 패드를 `unconnected-(U3-SPICLK-Pad22)` 라는 유사 네트로 내보낸다.
# IPC-D-356 네트명 필드가 14자라 **앞의 `unconnected-` 가 잘려 나가고** 뒤만 남는다.
#
#     원본   unconnected-(U3-SPICLK-Pad22)
#     d356   -SPICLK-PAD22)          ← 진짜 네트처럼 보인다
#
# 실측(ESP32-C3 오픈소스 보드): `.kicad_pcb` 의 unconnected 32개 중 `N/C` 로 온 것은
# 2개뿐이고 16개가 이 모양으로 왔다. 이름으로만 판단하면 R07 이 통째로 침묵한다.


def _kicad_style_board() -> str:
    """D2 만 진짜로 배선되고, D3 는 KiCad 식 유사 네트(패드 1개)."""
    lines = []
    for i, (pin, net) in enumerate(zip(LEFT, ["N/C", "N/C", "SENSE", "-SPICLK-PAD22)",
                                              "N/C", "N/C", "N/C"])):
        lines.append(rec(net, "U1", pin, x=-0.2635, y=0.7922 - 0.1 * i))
    for i, pin in enumerate(RIGHT):
        lines.append(rec("N/C", "U1", pin, x=0.3365, y=0.7922 - 0.1 * i))
    lines.append(rec("SENSE", "X1", "1", x=2.0, y=0.0))  # D2 의 상대편
    return board(*lines)


def test_positive_kicad_pseudo_net_is_still_unconnected():
    """유사 네트에 붙은 D3 를 코드가 쓰면 R07 이 떠야 한다. 이름은 진짜 네트처럼 생겼다."""
    findings = _run(_kicad_style_board(), {"a.ino": "void setup(){ pinMode(D3, INPUT); }"})
    assert len(findings) == 1, "이름만 보면 배선된 것처럼 보여 침묵한다 (미탐)"
    assert "D3" in findings[0].claim
    assert findings[0].severity is Severity.CRITICAL


def test_negative_kicad_board_real_wire_is_silent():
    """같은 보드에서 진짜로 배선된 D2 는 조용해야 한다. 고치면서 오탐이 늘면 안 된다."""
    findings = _run(_kicad_style_board(), {"a.ino": "void setup(){ pinMode(D2, OUTPUT); }"})
    assert findings == []
