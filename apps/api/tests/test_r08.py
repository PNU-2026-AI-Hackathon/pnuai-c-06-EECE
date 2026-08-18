"""R08 — 양성 / 음성 / 미해결."""

from __future__ import annotations

from pathlib import Path

from prefab.firmware import analyze as analyze_firmware
from prefab.firmware import load_directory
from prefab.netlist.d356 import parse, parse_text
from prefab.netlist.graph import Graph
from prefab.rules import r08_connected_but_unused as r08
from prefab.types import Context, Severity, Verdict

from _builder import board, rec
from test_r07 import LEFT, RIGHT, _kicad_style_board, _synth_board

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE = FIXTURES / "esp32-c6-presence-smart-light.d356"
FIRMWARE_DIR = FIXTURES / "esp32-c6-presence-smart-light.firmware"


def _run(netlist_text: str, sources: "dict[str, str]"):
    graph = Graph(parse_text(netlist_text))
    return r08.check(Context(netlist=graph, firmware=analyze_firmware(sources)))


def test_positive_real_board_one_finding():
    """EXPECTED.md 3절 — D5 한 건. D2 는 코드가 쓰므로 나오면 안 된다."""
    graph = Graph(parse(FIXTURE))
    firmware = analyze_firmware(load_directory(FIRMWARE_DIR))
    findings = r08.check(Context(netlist=graph, firmware=firmware))

    assert len(findings) == 1
    f = findings[0]
    assert f.net == "_IN_ACTIVE_LOW"
    assert "D5" in f.claim
    assert f.severity is Severity.WARNING
    assert f.verdict is Verdict.FAIL
    assert f.unresolved_reason is None


def test_negative_pin_the_code_uses_is_silent():
    text = _synth_board(["N/C", "N/C", "SENSE", "N/C", "N/C", "N/C", "N/C"])
    assert _run(text, {"a.ino": "void setup(){ pinMode(D2, OUTPUT); }"}) == []


def test_negative_unconnected_pins_are_not_this_rule():
    """배선이 없으면 R07 의 영역이다. R08 은 조용하다."""
    text = _synth_board(["N/C"] * 7)
    assert _run(text, {"a.ino": "void setup(){}"}) == []


def test_negative_power_and_ground_pins_are_excluded():
    """3V3 · GND · 5V 헤더 핀을 코드가 안 만진다고 경고하면 오탐 생성기가 된다."""
    text = _synth_board(["N/C"] * 7, ["5V_BUS", "GND_BUS", "3V3", "N/C", "N/C", "N/C", "N/C"])
    assert _run(text, {"a.ino": "void setup(){}"}) == []


def test_positive_when_code_uses_a_different_pin():
    text = _synth_board(["N/C", "N/C", "N/C", "N/C", "N/C", "RELAY_IN", "N/C"])
    findings = _run(text, {"a.ino": "void setup(){ pinMode(D2, OUTPUT); }"})
    assert len(findings) == 1
    assert "D5" in findings[0].claim


def test_unresolved_unknown_module_produces_nothing():
    """핀아웃을 못 알아보면 어느 핀인지 모른다. 모르면 판정하지 않는다."""
    text = board(rec("SIG", "U9", "AAAA", x=0.0, y=0.5), rec("SIG2", "U9", "BBBB", x=0.0, y=0.4))
    assert _run(text, {"a.ino": "void setup(){}"}) == []


def test_gpio_number_form_in_code_counts_as_use():
    """코드가 `21` 로 적었어도 D3 를 쓴 것이다. 실크로 안 적었다고 경고하면 오탐이다."""
    text = _synth_board(["N/C", "N/C", "N/C", "ECHO", "N/C", "N/C", "N/C"])
    assert _run(text, {"a.ino": "void setup(){ pinMode(21, INPUT); }"}) == []


def test_absence_evidence_has_a_null_line():
    """'없다'는 사실에는 가리킬 줄이 없다. line 을 지어내지 않는다 (계약 「부재도 근거다」)."""
    graph = Graph(parse(FIXTURE))
    firmware = analyze_firmware(load_directory(FIRMWARE_DIR))
    f = r08.check(Context(netlist=graph, firmware=firmware))[0]

    fw = [e for e in f.evidence if e.kind == "firmware"]
    assert len(fw) == 1
    assert fw[0].line is None
    assert fw[0].to_dict()["line"] is None
    assert "D5" in fw[0].snippet and "나오지 않습니다" in fw[0].snippet
    assert "106줄" in fw[0].snippet  # 무엇을 다 읽었는지 밝힌다
    assert fw[0].file == "smart_shoe_cabinet_v1.ino"


def test_netlist_evidence_names_the_resistor_role():
    """A-1 — 같은 네트의 저항이 풀업인지 풀다운인지 근거에 적힌다."""
    graph = Graph(parse(FIXTURE))
    firmware = analyze_firmware(load_directory(FIRMWARE_DIR))
    f = r08.check(Context(netlist=graph, firmware=firmware))[0]
    netlist_ev = next(e for e in f.evidence if e.kind == "netlist")
    assert "풀업" in netlist_ev.text
    assert "U1.D5" in netlist_ev.text


def test_check_is_a_pure_function():
    graph = Graph(parse(FIXTURE))
    ctx = Context(netlist=graph, firmware=analyze_firmware(load_directory(FIRMWARE_DIR)))
    assert [f.to_dict() for f in r08.check(ctx)] == [f.to_dict() for f in r08.check(ctx)]


def test_negative_kicad_pseudo_net_is_not_a_wire():
    """KiCad 유사 네트는 배선이 아니다. 코드가 안 써도 R08 이 뜨면 오탐이다.

    `-SPICLK-PAD22)` 는 `unconnected-(U3-SPICLK-Pad22)` 가 14자에서 잘린 것이고
    패드가 하나뿐이다. 이름만 보면 배선처럼 보여 "배선됐는데 코드가 안 쓴다"고 말하게 된다.
    """
    findings = _run(_kicad_style_board(), {"a.ino": "void setup(){ pinMode(D2, OUTPUT); }"})
    nets = [f.net for f in findings]
    assert "-SPICLK-PAD22)" not in nets, f"미연결 패드에 R08 오탐: {nets}"
