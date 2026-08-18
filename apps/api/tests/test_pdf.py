"""PDF → 쪽별 글자.

여기서 지키려는 것은 **쪽 번호가 맞는 것**이다. 번호가 어긋나면 추출기의 원문 대조가
통째로 무의미해진다 — 진짜 인용문을 지어낸 것으로 판정하거나 그 반대가 된다.

실제 데이터시트는 제조사 저작물이라 커밋하지 않는다. 합성 PDF 를 만들어 쓴다.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pdfplumber", reason="데이터시트 추출은 선택 의존성입니다")

from prefab.datasheet.pdf import THIN_PAGE_CHARS, PdfError, notes, read_pages  # noqa: E402
from tests._pdfbuild import build  # noqa: E402

BODY = [
    "A GPIO, IO level 3.3V",
    "DC 5V, power supply capacity>200mA",
    "Absolute Maximum Ratings",
]


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "datasheet.pdf"
    path.write_bytes(build(BODY))
    return path


def test_쪽_번호는_사람이_세는_대로_1부터(sample):
    pages = read_pages(sample)
    assert [p.number for p in pages] == [1, 2, 3]


def test_쪽마다_그_쪽_글자만_들어간다(sample):
    """쪽이 섞이면 원문 대조가 엉뚱한 쪽을 보게 된다."""
    pages = {p.number: p.text for p in read_pages(sample)}
    assert "3.3V" in pages[1] and "3.3V" not in pages[2]
    assert "Absolute Maximum" in pages[3]


def test_범위로_좁힐_수_있다(sample):
    """데이터시트는 정격 표가 뒤에 있다. 앞을 통째로 넘기면 토큰이 그만큼 든다."""
    pages = read_pages(sample, pages=range(2, 4))
    assert [p.number for p in pages] == [2, 3]
    assert "capacity>200mA" in pages[0].text


def test_범위를_좁혀도_원래_쪽_번호를_지킨다(sample):
    """1부터 다시 세면 인용문 검증이 전부 어긋난다."""
    assert read_pages(sample, pages=range(3, 4))[0].number == 3


def test_읽으며_눈에_띈_것을_보고한다(sample):
    out = " · ".join(notes(read_pages(sample)))
    assert "쪽 3개" in out


def test_글자가_거의_없는_쪽을_알려준다(tmp_path):
    """스캔 이미지 데이터시트는 이 경로로 못 읽는다. 아무 말이 없으면
    '값이 없는 부품'으로 오해하게 된다 (CLAUDE.md 2-4)."""
    path = tmp_path / "scan.pdf"
    path.write_bytes(build(["x", "A GPIO, IO level 3.3V " * 5]))
    out = " · ".join(notes(read_pages(path)))
    assert "글자가 거의 없는 쪽 1개" in out and "스캔 이미지" in out
    assert len("x") < THIN_PAGE_CHARS


def test_없는_파일은_죽지_않고_말한다(tmp_path):
    with pytest.raises(PdfError, match="파일이 없습니다"):
        read_pages(tmp_path / "없다.pdf")


def test_PDF가_아니면_말한다(tmp_path):
    junk = tmp_path / "a.pdf"
    junk.write_bytes("이건 PDF 가 아닙니다".encode())
    with pytest.raises(PdfError):
        read_pages(junk)


def test_뽑은_글자가_추출기_검증을_통과한다(sample):
    """PDF 읽기와 원문 대조가 같은 글자를 보는지 — 두 모듈의 접합부다."""
    from prefab.datasheet.extract import _verify

    pages = read_pages(sample)
    raw = {"facts": [{
        "field": "voh_max", "value_number": 3.3, "value_text": None, "unit": "V",
        "table": "T", "page": 1, "quote": "A GPIO, IO level 3.3V",
        "confidence": "high", "reason": None,
    }]}
    r = _verify(raw, mpn="X", pages=pages, source_url="u", source_tier="official")
    assert r.ok and len(r.facts) == 1
