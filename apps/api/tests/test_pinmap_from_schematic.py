"""회로도 넷리스트에서도 핀맵이 풀린다 — 부품번호 + 핀 이름으로.

**차별 규칙 절반이 안 돌고 있었다.**

`pinmap._match_part` 는 **X좌표 열 서명**으로 모듈을 알아본다. IPC-D-356 은 핀 이름을
4자로 자르니 기하 말고 방법이 없어서 그렇게 만들었다. 그런데 회로도 넷리스트에는
**좌표가 아예 없다.** 그래서 그 형식으로 올린 보드에서는 핀맵이 통째로 비었고,
`pinmap.gpio_pads()` 를 도는 R07·R08 이 아무 말도 못 했다.

드리프트 데모를 만들다 발견했다 — 센서 핀을 D2 에서 D4 로 옮겼는데 **"변화 없음"**
이 나왔다. 우리 REV2 보드가 바로 그 형식이다.

회로도 넷리스트는 좌표가 없는 대신 **부품번호를 실어 온다.** 그러면 모듈을 알 수 있고,
핀 이름도 안 잘린 채 오므로 실크 표로 바로 풀린다.
"""

from __future__ import annotations

from pathlib import Path

from prefab.firmware import analyze as analyze_firmware
from prefab.netlist.detect import parse_any
from prefab.netlist.graph import Graph
from prefab.rules import r07_pin_not_connected as r07
from prefab.rules import r08_connected_but_unused as r08
from prefab.types import Context

BOARD = Path(__file__).parent.parent / "board"

FIRMWARE = {"a.ino": (
    "#define PRESENCE_PIN D2\n"
    "#define RELAY_PIN D5\n"
    "void setup(){ pinMode(PRESENCE_PIN, INPUT); pinMode(RELAY_PIN, OUTPUT); }\n"
)}


def _graph(text: str) -> Graph:
    return Graph(parse_any(text))


def _board_text() -> str:
    return BOARD.joinpath("board.net.xml").read_text(encoding="utf-8")


def test_부품번호와_핀_이름으로_핀맵이_풀린다():
    g = _graph(_board_text())
    pads = {(p.silk, p.gpio) for p in g.pinmap.gpio_pads()}
    assert ("D2", 2) in pads, pads
    assert ("D5", 23) in pads, pads
    assert g.pinmap.modules_matched.get("U1") == "XIAO-ESP32C6"


def test_모듈을_못_알아보면_아무것도_안_붙인다():
    """부품번호가 없으면 그 부품에 무슨 핀이 있는지도 모른다. 지어내지 않는다."""
    text = _board_text().replace('<field name="MPN">XIAO-ESP32C6</field>', "")
    assert _graph(text).pinmap.gpio_pads() == []


def test_이름_몇_개_맞은_것으로_모듈을_단정하지_않는다():
    """심볼이 헤더를 다르게 부르면 GPIO 번호를 지어내는 셈이다.

    그 위에 올라가는 R07·R08 이 통째로 거짓말이 된다.
    """
    text = _board_text()
    for silk in ("5V", "GND", "3V3", "D5"):
        text = text.replace(f'pinfunction="{silk}"', f'pinfunction="X_{silk}"')
    assert _graph(text).pinmap.gpio_pads() == []


# ── 그래서 R07·R08 이 돈다 ──────────────────────────────────────────


def test_정상_보드에서는_조용하다():
    g = _graph(_board_text())
    ctx = Context(netlist=g, firmware=analyze_firmware(FIRMWARE))
    assert r07.check(ctx) == []
    assert r08.check(ctx) == []


def test_핀이_옮겨가면_양쪽에서_짚는다():
    """센서 출력이 D2 에서 D4 로 갔는데 코드는 그대로다.

    R07  코드가 쓰는 D2 가 회로도에 없다
    R08  회로도가 배선한 D4 를 코드가 안 쓴다
    """
    text = _board_text().replace(
        '<node ref="U1" pin="4" pinfunction="D2"/>',
        '<node ref="U1" pin="6" pinfunction="D4"/>',
    )
    ctx = Context(netlist=_graph(text), firmware=analyze_firmware(FIRMWARE))

    moved = r07.check(ctx)
    assert len(moved) == 1, [f.claim for f in moved]
    assert "D2" in moved[0].claim and "한 번도 나오지 않습니다" in moved[0].claim

    unused = r08.check(ctx)
    assert len(unused) == 1, [f.claim for f in unused]
    assert "D4" in unused[0].claim


def test_회로도에_없는_핀도_근거를_지어내지_않는다():
    """가리킬 네트가 없다. `net` 은 None 이고 근거는 **모듈 표**라고 밝힌다."""
    text = _board_text().replace(
        '<node ref="U1" pin="4" pinfunction="D2"/>',
        '<node ref="U1" pin="6" pinfunction="D4"/>',
    )
    f = r07.check(Context(netlist=_graph(text), firmware=analyze_firmware(FIRMWARE)))[0]
    assert f.net is None
    netlist_ev = next(e for e in f.evidence if e.kind == "netlist")
    assert "핀아웃 표" in netlist_ev.text, netlist_ev.text
    # 코드 근거는 실제 줄이어야 한다
    assert any(e.kind == "firmware" and e.line for e in f.evidence)


def test_모듈에_없는_핀은_판정하지_않는다():
    """코드가 D42 를 쓴다. 그런 핀이 이 모듈에 없으면 아무 말도 안 한다."""
    fw = {"a.ino": "void setup(){ pinMode(D42, OUTPUT); }"}
    ctx = Context(netlist=_graph(_board_text()), firmware=analyze_firmware(fw))
    assert r07.check(ctx) == []
