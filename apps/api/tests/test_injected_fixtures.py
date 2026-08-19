"""결함 주입 픽스처의 **곁가지 핀**이 깨끗한지 검사한다.

같은 실수를 세 번 했다.

    GPIO9  를 "평범한 핀" 으로 골랐는데 C6 스트래핑이었다
    GPIO8  을 "평범한 핀" 으로 골랐는데 구형 ESP32 플래시였다
    GPIO16 을 "평범한 핀" 으로 골랐는데 C6 의 UART TX 였다

셋 다 측정기가 오탐으로 잡아줘서 알았다. 규칙이 아니라 **픽스처가 틀린 것**이었다.
칩 표가 자라면 어제의 평범한 핀이 오늘 특별해진다. 사람이 기억할 일이 아니다.

케이스마다 검사하지 않는다 — 음성 케이스도 일부러 특별한 핀을 쓸 때가 있다
(`r03-strapping-pullup` 은 스트래핑 핀에 풀업을 달아 "이건 정상" 을 고정한다).
막을 곳은 **곁가지 핀을 고르는 자리** 하나다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from prefab.chips import CHIPS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _taken(chip) -> "dict[int, str]":
    named = {
        "입력 전용": chip.input_only,
        "플래시": chip.spi_flash,
        "스트래핑": chip.strapping,
        "ADC1": chip.adc1,
        "ADC2": chip.adc2,
        "부팅 중 출력": chip.boot_output,
    }
    out: dict[int, str] = {}
    for label, pins in named.items():
        for g in pins:
            out.setdefault(g, label)
    return out


@pytest.mark.parametrize("chip_id", sorted(CHIPS))
def test_곁가지_핀은_표에_안_걸린다(chip_id):
    from make_injected import plain_pins

    taken = _taken(CHIPS[chip_id])
    hit = {g: taken[g] for g in plain_pins(chip_id) if g in taken}
    assert not hit, (
        f"{chip_id} 의 곁가지 후보가 표에 걸려 있다: "
        + ", ".join(f"GPIO{g}={what}" for g, what in sorted(hit.items()))
    )


def test_곁가지_후보가_남아_있다():
    """표가 자라다 보면 깨끗한 핀이 동날 수 있다. 그때는 픽스처 전략을 바꿔야 한다."""
    from make_injected import plain_pins

    for chip_id in CHIPS:
        assert len(plain_pins(chip_id)) >= 4, f"{chip_id} 에 쓸 깨끗한 핀이 4개도 없다"
