"""모듈 핀아웃 — 4자로 뭉친 이름을 좌표로 되돌린다.

이 파일이 통과하지 않으면 R07 · R08 은 전부 거짓말이다.
"""

from __future__ import annotations

from pathlib import Path

from prefab.chips import MODULES, XIAO_ESP32C6
from prefab.netlist.d356 import parse, parse_text
from prefab.netlist.pinmap import resolve

from _builder import board, rec

FIXTURE = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"

#: EXPECTED.md 1절의 표. 두 열의 Y 는 같고 X 로만 갈린다.
LEFT_COLUMN_X = -0.2635
RIGHT_COLUMN_X = 0.3365


def test_module_is_recognised():
    pm = resolve(parse(FIXTURE))
    assert pm.modules_matched == {"U1": "XIAO-ESP32C6"}


def test_three_sdio_pads_become_three_different_pins():
    """이게 이 파일의 존재 이유다. SDIO ×3 → D3 · D4 · D5."""
    pm = resolve(parse(FIXTURE))
    sdio = sorted(i.silk for i in pm.all() if i.pin == "SDIO")
    assert sdio == ["D3", "D4", "D5"]
    assert sorted(i.silk for i in pm.all() if i.pin == "LP-G") == ["D0", "D1", "D2"]


def test_gpio_numbers_match_the_chips_table():
    """docs/CHIPS.md 의 실크 → GPIO 표와 일치해야 한다."""
    pm = resolve(parse(FIXTURE))
    got = {i.silk: i.gpio for i in pm.gpio_pads()}
    assert got == {
        "D0": 0, "D1": 1, "D2": 2,
        "D3": 21, "D4": 22, "D5": 23,
        "D6": 16, "D7": 17, "D8": 19, "D9": 20, "D10": 18,
    }


def test_connected_pins_are_the_two_the_expected_doc_names():
    """D2 → PRESENCE_3V3, D5 → _IN_ACTIVE_LOW. 나머지 GPIO 는 전부 N/C."""
    nl = parse(FIXTURE)
    pm = resolve(nl)
    connected = {
        i.silk: nl.net_at(i.ref, i.pin, i.x, i.y)
        for i in pm.gpio_pads()
        if not nl.is_unconnected(nl.net_at(i.ref, i.pin, i.x, i.y))
    }
    assert connected == {"D2": "PRESENCE_3V3", "D5": "_IN_ACTIVE_LOW"}


def test_power_header_pins_have_no_gpio_number():
    pm = resolve(parse(FIXTURE))
    power = {i.silk for i in pm.all() if i.gpio is None}
    assert power == {"5V", "GND", "3V3"}


def test_columns_are_ordered_by_descending_y():
    """Y 내림차순이 실크 순서다. 두 열의 Y 는 같고 X 로만 갈린다."""
    pm = resolve(parse(FIXTURE))

    def column(x: float) -> list[str]:
        pads = [i for i in pm.all() if abs(i.x - x) < 0.01]
        return [i.silk for i in sorted(pads, key=lambda i: -i.y)]

    assert column(LEFT_COLUMN_X) == ["D0", "D1", "D2", "D3", "D4", "D5", "D6"]
    assert column(RIGHT_COLUMN_X) == ["5V", "GND", "3V3", "D10", "D9", "D8", "D7"]


def test_find_by_silk_and_by_gpio_agree():
    pm = resolve(parse(FIXTURE))
    assert pm.find(silk="D5").gpio == 23
    assert pm.find(gpio=23).silk == "D5"
    assert pm.find(silk="D99") is None


def test_unknown_board_gets_no_labels():
    """서명이 안 맞으면 아무것도 붙이지 않는다. 절반만 믿지 않는다."""
    text = board(
        *[rec("N/C", "U9", f"P{i}", x=0.0, y=0.7922 - 0.1 * i) for i in range(7)],
        *[rec("N/C", "U9", f"Q{i}", x=0.6, y=0.7922 - 0.1 * i) for i in range(7)],
    )
    assert len(resolve(parse_text(text))) == 0


def test_half_matching_board_is_rejected():
    """오른쪽 열만 맞고 왼쪽이 다르면 다른 보드다. 라벨을 붙이지 않는다."""
    right = ["5V", "GND", "3V3", "D10_", "D9_M", "D8_S", "D7_R"]
    text = board(
        *[rec("N/C", "U9", f"X{i}", x=0.0, y=0.7922 - 0.1 * i) for i in range(7)],
        *[rec("N/C", "U9", name, x=0.6, y=0.7922 - 0.1 * i) for i, name in enumerate(right)],
    )
    assert len(resolve(parse_text(text))) == 0


def test_module_table_is_self_consistent():
    """실크는 유일하고, GPIO 번호도 유일해야 한다."""
    silks = [p.silk for col in XIAO_ESP32C6.columns for p in col]
    assert len(silks) == len(set(silks))
    gpios = [g for g in XIAO_ESP32C6.silk_to_gpio.values()]
    assert len(gpios) == len(set(gpios))
    assert XIAO_ESP32C6.gpio_to_silk[23] == "D5"
    assert XIAO_ESP32C6.id in MODULES
