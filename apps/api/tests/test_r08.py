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


# ── 주변장치가 모는 핀 (오탐 수정) ──────────────────────────────────
#
# 오픈소스 ESP32-C3 보드 4개 리비전에서 `USB_D+` · `USB_D-` 가 리비전마다
# 2건씩 떴다. USB 는 전용 주변장치가 몰기 때문에 코드에 `pinMode` 가 없는 것이
# **정상**이다 — 오히려 만지면 인터페이스가 죽는다.
#
# 우리 픽스처에는 USB 를 뽑아 쓰는 보드가 없어서 한 번도 안 만났다.
# 여기 고정해서 다시는 못 돌아오게 한다.


#: **핀을 하나는 쓰는** 펌웨어. 보드에 없는 GPIO40 을 쓴다.
#:
#: R08 은 코드에서 핀을 0개 읽으면 아무 말도 하지 않는다 — "다 읽어봤는데 없더라" 가
#: 성립하지 않기 때문이다. 그래서 억제 로직을 시험하려면 **파서가 뭔가는 읽은** 상태여야
#: 한다. 보드와 무관한 핀을 쓰는 이유는 그것이 판정 대상에 끼지 않게 하기 위해서다.
FW_UNRELATED = {"a.ino": "void setup(){ pinMode(40, OUTPUT); }"}


def _board_with_counterpart(net: str, other_ref: str, other_pin: str) -> str:
    """XIAO 헤더의 D2 를 `net` 에 물리고, 그 반대편 패드 이름을 지정한다."""
    lines = [
        rec(n, "U1", pin, x=-0.2635, y=0.7922 - 0.1 * i)
        for i, (pin, n) in enumerate(zip(LEFT, ["N/C", "N/C", net, "N/C", "N/C", "N/C", "N/C"]))
    ]
    lines += [
        rec("N/C", "U1", pin, x=0.3365, y=0.7922 - 0.1 * i)
        for i, pin in enumerate(RIGHT)
    ]
    lines.append(rec(net, other_ref, other_pin, x=2.0, y=0.0))
    return board(*lines)


def test_positive_control_ordinary_counterpart_still_warns():
    """대조군 — 같은 보드 모양인데 상대편이 평범한 패드면 경고가 나야 한다.

    이게 없으면 아래 음성 테스트가 '원래 안 뜨는 것' 을 확인한 셈이 된다.
    """
    text = _board_with_counterpart("SENSE", "X1", "1")
    assert len(_run(text, FW_UNRELATED)) == 1


def test_negative_usb_data_pin_is_not_a_finding():
    """상대편이 USB 커넥터의 `D-` 다. **반대쪽 핀이 스스로 밝힌다.**"""
    text = _board_with_counterpart("USB_DM", "J1", "D-")
    # 무관한 핀을 쓰는 펌웨어다 — 0핀 가드가 아니라 **억제 로직**이 일해야 한다
    assert _run(text, FW_UNRELATED) == []


def test_negative_usb_suppression_does_not_depend_on_net_name():
    """네트 이름은 아무렇게나 붙을 수 있다. 판정 근거는 상대편 핀 이름이다."""
    text = _board_with_counterpart("NET_42", "J1", "D+")
    # 무관한 핀을 쓰는 펌웨어다 — 0핀 가드가 아니라 **억제 로직**이 일해야 한다
    assert _run(text, FW_UNRELATED) == []


def test_negative_lowercase_pin_name_also_counts():
    text = _board_with_counterpart("USB_DP", "J1", "d+")
    # 무관한 핀을 쓰는 펌웨어다 — 0핀 가드가 아니라 **억제 로직**이 일해야 한다
    assert _run(text, FW_UNRELATED) == []


def test_positive_similar_looking_pin_name_still_warns():
    """`D2` 는 USB 데이터 핀이 아니라 그냥 2번 핀이다. 넓게 잡으면 미탐이 된다."""
    text = _board_with_counterpart("SENSE", "J1", "D2")
    assert len(_run(text, FW_UNRELATED)) == 1


def test_negative_usb_pin_name_from_schematic_netlist():
    """실제로 오탐이 난 경로 — 회로도 넷리스트(kicadxml).

    MCU 쪽 핀은 `GPIO18` 이라고만 말한다. 실리콘이 그 핀을 USB 로도 쓴다는 걸
    핀 이름은 모른다. 그래서 상대편(USB-C 커넥터)의 `D-` 를 본다.
    """
    from prefab.netlist.kicadxml import parse_text as parse_xml

    xml = """<?xml version="1.0" encoding="UTF-8"?>
<export version="E">
  <components>
    <comp ref="U3"><value>ESP32-C3</value></comp>
    <comp ref="U1"><value>USB-C-16P-SMD</value></comp>
    <comp ref="R1"><value>100k</value></comp>
  </components>
  <nets>
    <net code="1" name="USB_D-">
      <node ref="U3" pin="25" pinfunction="GPIO18_25"/>
      <node ref="U1" pin="A7" pinfunction="D-"/>
    </net>
    <net code="2" name="EXTI">
      <node ref="U3" pin="6" pinfunction="GPIO2_6"/>
      <node ref="R1" pin="2"/>
    </net>
    <net code="3" name="ADC"><node ref="U3" pin="8" pinfunction="GPIO3_8"/>
      <node ref="R1" pin="1"/></net>
    <net code="4" name="BTN"><node ref="U3" pin="15" pinfunction="GPIO9_15"/>
      <node ref="U1" pin="A1" pinfunction="GND"/></net>
  </nets>
</export>"""
    graph = Graph(parse_xml(xml))
    findings = r08.check(Context(netlist=graph, firmware=analyze_firmware(FW_UNRELATED)))

    nets = {f.net for f in findings}
    assert "USB_D-" not in nets, "USB 데이터 핀은 코드가 안 만지는 것이 정상이다"
    # 나머지는 그대로 잡아야 한다 — 억제가 규칙 전체를 죽이면 안 된다
    assert nets == {"EXTI", "ADC", "BTN"}


def test_negative_chip_table_knows_usb_pins_without_connector_names():
    """**커넥터가 핀 이름을 안 밝혀도** 칩 표가 알면 억제된다.

    앞의 테스트들은 상대편이 `D-` 라고 스스로 밝히는 경우다. 그런데 커넥터를
    범용 심볼(`Pin_1`)로 그리면 그 이름이 없다 — 실측한 저장소 하나가 그랬다.
    칩을 알면 그 경우에도 안다: ESP32-S3 의 GPIO19·20 은 USB Serial/JTAG 다.
    """
    from prefab.netlist.kicadxml import parse_text as parse_xml

    xml = """<?xml version="1.0"?><export version="E">
  <components>
    <comp ref="U1"><value>ESP32-S3</value>
      <fields><field name="MPN">ESP32-S3-WROOM-1</field></fields></comp>
    <comp ref="J1"><value>Conn_01x04</value></comp>
  </components>
  <nets>
    <net code="1" name="N1"><node ref="U1" pin="20" pinfunction="GPIO19_20"/>
      <node ref="J1" pin="1" pinfunction="Pin_1_1"/></net>
    <net code="2" name="N2"><node ref="U1" pin="21" pinfunction="GPIO20_21"/>
      <node ref="J1" pin="2" pinfunction="Pin_2_2"/></net>
    <net code="3" name="SENSE"><node ref="U1" pin="5" pinfunction="GPIO4_5"/>
      <node ref="J1" pin="3" pinfunction="Pin_3_3"/></net>
    <net code="4" name="LED"><node ref="U1" pin="6" pinfunction="GPIO5_6"/>
      <node ref="J1" pin="4" pinfunction="Pin_4_4"/></net>
  </nets></export>"""
    graph = Graph(parse_xml(xml))
    findings = r08.check(
        Context(netlist=graph, firmware=analyze_firmware(FW_UNRELATED))
    )

    nets = {f.net for f in findings}
    # 커넥터는 `Pin_1` 이라고만 말한다. 칩 표가 아니면 못 걸러낸다
    assert nets == {"SENSE", "LED"}, nets


def test_positive_usb_suppression_needs_the_right_chip():
    """구형 ESP32 에는 내장 USB 가 없다. GPIO19·20 은 평범한 핀이다.

    칩을 안 가리고 번호만 보면 여기서 미탐이 난다.
    """
    from prefab.netlist.kicadxml import parse_text as parse_xml

    xml = """<?xml version="1.0"?><export version="E">
  <components>
    <comp ref="U1"><value>ESP32</value>
      <fields><field name="MPN">ESP32-WROOM-32</field></fields></comp>
    <comp ref="J1"><value>Conn_01x04</value></comp>
  </components>
  <nets>
    <net code="1" name="N1"><node ref="U1" pin="20" pinfunction="GPIO19_20"/>
      <node ref="J1" pin="1" pinfunction="Pin_1_1"/></net>
    <net code="2" name="N2"><node ref="U1" pin="21" pinfunction="GPIO21_21"/>
      <node ref="J1" pin="2" pinfunction="Pin_2_2"/></net>
    <net code="3" name="N3"><node ref="U1" pin="23" pinfunction="GPIO22_23"/>
      <node ref="J1" pin="3" pinfunction="Pin_3_3"/></net>
    <net code="4" name="N4"><node ref="U1" pin="24" pinfunction="GPIO23_24"/>
      <node ref="J1" pin="4" pinfunction="Pin_4_4"/></net>
  </nets></export>"""
    graph = Graph(parse_xml(xml))
    findings = r08.check(
        Context(netlist=graph, firmware=analyze_firmware(FW_UNRELATED))
    )
    assert "N1" in {f.net for f in findings}


def test_negative_firmware_with_no_pins_reported_says_nothing():
    """**핀을 하나도 못 읽었으면 아무 말도 하지 않는다.**

    이 규칙의 주장은 "다 읽어봤는데 이 핀이 없더라" 다. 0개를 읽은 상태에서는
    코드가 안 쓰는 게 아니라 **우리가 못 읽은 것**이다 (헌법 2-2).

    실보드에서 이걸로 오탐이 쏟아졌다 — ESPHome 보드는 핀을 YAML 로 정하고
    (우리 파서는 C/C++ 만 안다) 라이브러리만 든 zip 도 마찬가지다.
    각각 9건 · 13건이 떴다.
    """
    text = _board_with_counterpart("SENSE", "X1", "1")
    assert _run(text, {"a.ino": "// 핀을 안 쓰는 코드"}) == []
    # 대조군 — 하나라도 읽으면 원래대로 경고한다
    assert len(_run(text, FW_UNRELATED)) == 1
