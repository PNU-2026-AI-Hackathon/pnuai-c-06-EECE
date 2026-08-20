"""칩 표 — 값이 출처와 맞는지, 그리고 표끼리 모순이 없는지.

`docs/CHIPS.md` 가 진실이고 `chips/__init__.py` 는 사본이다. 사본이 조용히
어긋나면 **R01·R02·R03·R05·R09 다섯 개가 통째로 틀린다.** 여기서 막는다.

칩을 새로 넣을 때 이 파일이 요구하는 것은 하나다 —
**출처에서 읽은 값을 그대로 적었는가.** 값을 여기 다시 적어 두는 이유가 그것이다.
"""

from __future__ import annotations

import pytest

from prefab.chips import CHIPS, ESP32S3
from prefab.rules.r01_unusable_pin import _chip_from_mpn

# ── 표끼리 모순이 없는가 (모든 칩) ──────────────────────────────────


@pytest.mark.parametrize("chip", CHIPS.values(), ids=list(CHIPS))
def test_ADC1_과_ADC2_는_겹치지_않는다(chip):
    assert not set(chip.adc1) & set(chip.adc2)


@pytest.mark.parametrize("chip", CHIPS.values(), ids=list(CHIPS))
def test_플래시_핀은_ADC_와도_스트래핑과도_겹치지_않는다(chip):
    """겹치면 둘 중 하나가 틀린 것이다. 실제로 겹치는 칩이 나오면 표를 고친다."""
    flash = set(chip.spi_flash)
    assert not flash & set(chip.adc1)
    assert not flash & set(chip.adc2)
    assert not flash & set(chip.strapping)


@pytest.mark.parametrize("chip", CHIPS.values(), ids=list(CHIPS))
def test_부팅_로그_핀은_부팅_출력_목록_안에_있다(chip):
    """로그가 나가는 핀은 당연히 부팅 때 출력이 나오는 핀이다."""
    if chip.boot_log_tx is None:
        return
    assert chip.boot_log_tx in chip.boot_output


@pytest.mark.parametrize("chip", CHIPS.values(), ids=list(CHIPS))
def test_핀_번호가_음수가_아니다(chip):
    for field in (chip.input_only, chip.spi_flash, chip.strapping, chip.adc1, chip.adc2, chip.boot_output):
        assert all(isinstance(p, int) and p >= 0 for p in field)


# ── ESP32-S3 — 출처에서 읽은 값 그대로 ──────────────────────────────
#
# 근거는 docs/CHIPS.md 「ESP32-S3」 절과 그 아래 출처 목록에 있다.
# 전부 1차 출처(Espressif 공식 문서·ESP-IDF 소스)에서 확인했다 (2026-08-20).


def test_S3_는_입력_전용_핀이_없다():
    """ESP-IDF: "The ESP32-S3 has no input-only GPIO pins."

    **비어 있는 것이 "모른다"가 아니라 "없다"인 경우다.** 구형 ESP32 와 다르다.
    """
    assert ESP32S3.input_only == ()


def test_S3_스트래핑은_네_개다():
    assert ESP32S3.strapping == (0, 3, 45, 46)


def test_S3_플래시는_GPIO26에서_32까지다():
    assert ESP32S3.spi_flash == (26, 27, 28, 29, 30, 31, 32)


def test_S3_옥타_플래시_핀은_일부러_뺐다():
    """GPIO33~37 은 **옥타 플래시·PSRAM 보드에만** 해당한다.

    표에 넣으면 쿼드 보드에서 R02 가 오탐을 낸다 (헌법 2-3).
    보드가 옥타라고 확인되면 그때 넣는다 — 그때 이 테스트를 고친다.
    """
    assert not set(range(33, 38)) & set(ESP32S3.spi_flash)


def test_S3_ADC_채널():
    """esp-idf/components/soc/esp32s3/include/soc/adc_channel.h 를 그대로 읽었다."""
    assert ESP32S3.adc1 == tuple(range(1, 11))
    assert ESP32S3.adc2 == tuple(range(11, 21))


def test_S3_부팅_출력은_U0TXD_하나뿐이다():
    """C6 와 같은 이유다 — **없어서가 아니라 못 찾아서** 하나뿐이다.

    부팅 글리치 핀 목록을 공식 문서에서 못 찾았다. 지어내면 R09 가 오탐을 낸다.
    """
    assert ESP32S3.boot_output == (43,)
    assert ESP32S3.boot_log_tx == 43


def test_S3_스트래핑_GPIO3_이_ADC1_과_겹친다는_것을_알고_있다():
    """겹침 자체가 정보다. 모르고 지나가면 그 핀에서 조용히 틀린다."""
    assert 3 in ESP32S3.strapping
    assert 3 in ESP32S3.adc1


# ── 부품번호로 S3 를 알아보는가 ─────────────────────────────────────


@pytest.mark.parametrize(
    "mpn",
    ["ESP32-S3", "ESP32-S3-WROOM-1", "ESP32-S3-MINI-1", "XIAO ESP32S3", "esp32s3"],
)
def test_부품번호에서_S3_를_알아본다(mpn):
    chip = _chip_from_mpn(mpn)
    assert chip is not None and chip.id == "esp32s3", mpn


def test_S3_가_구형_ESP32_로_잘못_걸리지_않는다():
    """`esp32s3` 안에 `esp32` 가 들어 있다. 긴 id 부터 봐야 한다."""
    assert _chip_from_mpn("ESP32-S3-WROOM-1").id == "esp32s3"
    assert _chip_from_mpn("ESP32-C6-WROOM-1").id == "esp32c6"
    assert _chip_from_mpn("ESP32-WROOM-32").id == "esp32"
