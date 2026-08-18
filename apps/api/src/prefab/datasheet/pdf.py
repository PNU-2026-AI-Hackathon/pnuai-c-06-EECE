"""PDF → 쪽별 글자.

추출기(`extract.py`)가 쪽 번호를 알아야 인용문을 원문과 대조할 수 있다.
그래서 여기서 하는 일은 글자를 뽑는 것보다 **쪽 경계를 지키는 것**이다.

`pdfplumber` 는 선택 의존성이다. 없으면 사람이 손으로 옮긴 글자를 넣어도 된다 —
`extract.Page` 만 만들면 된다.
"""

from __future__ import annotations

from pathlib import Path

from .extract import Page

#: 글자가 이보다 적은 쪽은 표지·목차·그림쪽일 가능성이 높다.
#: 버리지는 않는다. 다만 몇 쪽이 그런지 세어서 알려준다.
THIN_PAGE_CHARS = 40


class PdfError(RuntimeError):
    """PDF 를 열지 못했다."""


def read_pages(path: str | Path, *, pages: range | None = None) -> list[Page]:
    """PDF 를 쪽별로 읽는다. 쪽 번호는 사람이 세는 대로 1부터다.

    `pages` 로 범위를 좁힐 수 있다. 데이터시트는 정격 표가 보통 뒤쪽에 있어서
    앞의 소개 쪽을 통째로 넘길 이유가 없다 — 토큰이 그만큼 든다.
    """
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - 설치 여부에 따름
        raise PdfError(
            "pdfplumber 가 없습니다. `pip install pdfplumber` 하거나 "
            "글자를 직접 넘겨 주세요 (extract.Page)"
        ) from exc

    path = Path(path)
    if not path.exists():
        raise PdfError(f"파일이 없습니다: {path}")

    out: list[Page] = []
    try:
        with pdfplumber.open(path) as doc:
            for i, page in enumerate(doc.pages, start=1):
                if pages is not None and i not in pages:
                    continue
                out.append(Page(number=i, text=page.extract_text() or ""))
    except PdfError:
        raise
    except Exception as exc:
        raise PdfError(f"PDF 를 읽지 못했습니다: {exc}") from exc

    if not out:
        raise PdfError("읽어낸 쪽이 없습니다")
    return out


def notes(pages: list[Page]) -> list[str]:
    """읽으며 눈에 띈 것. **조용히 넘기지 않는다** (CLAUDE.md 2-4).

    글자가 거의 없는 쪽은 보통 스캔 이미지다. 그런 데이터시트는 이 경로로는
    값을 못 뽑는데, 아무 말이 없으면 "값이 없는 부품"으로 오해하게 된다.
    """
    thin = [p.number for p in pages if len(p.text.strip()) < THIN_PAGE_CHARS]
    out = [f"쪽 {len(pages)}개 · 글자 {sum(len(p.text) for p in pages):,}자"]
    if thin:
        out.append(
            f"글자가 거의 없는 쪽 {len(thin)}개 ({', '.join(map(str, thin[:8]))}) "
            "— 스캔 이미지면 이 경로로는 못 읽습니다"
        )
    return out
