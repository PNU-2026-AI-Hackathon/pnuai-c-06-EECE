"""데이터시트가 문장으로 적는 것을 규칙이 보는 상수로 옮긴다.

**LLM 이 읽고 코드가 정규화한다** (헌법 2-1 과 같은 모양).

데이터시트는 `Open Drain Charge Status Output ... otherwise pin is in high impedance
state` 처럼 적는다. 추출기는 그 문장을 그대로 실어 오고(자유 텍스트라 스키마가 못 막는다),
규칙은 `open-drain` 상수와 비교한다. 그 사이가 비면 **사실이 DB 에 있는데도 아무것도
해제되지 않는다.** 조용한 실패다.

실제로 한 번 밟았다. 정규화를 붙였는데 `field == OUTPUT_TYPE` 을 `item["field"]`
대신 `field` 로 써서, 모듈에 있던 `dataclasses.field` 와 비교하느라 **항상 거짓**이었다.
예외도 안 나고 값만 안 바뀌었다.
"""

from __future__ import annotations

import pytest

from prefab.datasheet.extract import _fact
from prefab.datasheet.facts import OPEN_DRAIN, OUTPUT_TYPE, PUSH_PULL, normalize_output_type


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Open Drain (CHRG/STDBY 상태 출력 핀 6, 7)", OPEN_DRAIN),
        ("Open drain (CHRG / STDBY status output pins)", OPEN_DRAIN),
        ("open-drain", OPEN_DRAIN),
        ("Open Collector", OPEN_DRAIN),   # 판정에는 같은 뜻이다
        ("오픈드레인", OPEN_DRAIN),
        ("push-pull", PUSH_PULL),
        ("Totem pole output", PUSH_PULL),
    ],
)
def test_문장을_상수로_옮긴다(raw, expected):
    assert normalize_output_type(raw) == expected


def test_둘_다_나오면_손대지_않는다():
    """`핀6은 오픈드레인, CE 는 푸시풀` 을 한쪽으로 뭉개면 없는 사실을 만드는 것이다."""
    text = "핀6은 오픈드레인, CE 는 푸시풀"
    assert normalize_output_type(text) == text


@pytest.mark.parametrize("value", [None, 3.3, 5, "CMOS", ""])
def test_모르는_것은_그대로_둔다(value):
    assert normalize_output_type(value) == value


# ── 추출기가 실제로 이걸 부르는가 ────────────────────────────────────


def _item(field: str) -> dict:
    return {"field": field, "unit": None, "table": "Pin description",
            "page": 2, "quote": "Open Drain Charge Status Output", "confidence": "high",
            "reason": None}


def test_추출기가_output_type_을_정규화한다():
    """**이 테스트가 없어서 조용히 지나갔다.** 값만 안 바뀌고 예외는 안 났다."""
    row = _fact(_item(OUTPUT_TYPE), value="Open Drain (CHRG/STDBY 상태 출력 핀 6, 7)")
    assert row["value"] == OPEN_DRAIN


def test_다른_항목은_건드리지_않는다():
    """숫자 항목에 문자열 정규화가 끼면 안 된다."""
    assert _fact(_item("vcc_nominal"), value=5)["value"] == 5
    assert _fact(_item("io_level"), value="TTL or CMOS")["value"] == "TTL or CMOS"
