"""테스트용 최소 PDF 생성기.

실제 데이터시트는 제조사 저작물이라 **MIT 리포에 커밋하지 않는다** (넷리스트 때와 같은
이유다). 그래서 쪽 번호와 글자만 확인할 수 있는 최소 PDF 를 여기서 만든다.
"""

from __future__ import annotations


def _obj(n: int, body: str) -> str:
    return f"{n} 0 obj\n{body}\nendobj\n"


def build(pages: list[str]) -> bytes:
    """쪽마다 글자 한 줄이 든 PDF 를 만든다. 쪽 수는 `len(pages)`."""
    n_pages = len(pages)
    # 1=Catalog, 2=Pages, 3=Font, 그 뒤로 쪽마다 Page + Contents 두 개씩
    page_ids = [4 + 2 * i for i in range(n_pages)]
    parts = [
        _obj(1, "<< /Type /Catalog /Pages 2 0 R >>"),
        _obj(2, f"<< /Type /Pages /Kids [{' '.join(f'{i} 0 R' for i in page_ids)}]"
                f" /Count {n_pages} >>"),
        _obj(3, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
    ]
    for i, text in enumerate(pages):
        pid, cid = page_ids[i], page_ids[i] + 1
        stream = f"BT /F1 12 Tf 72 720 Td ({_escape(text)}) Tj ET"
        parts.append(_obj(pid,
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            f" /Resources << /Font << /F1 3 0 R >> >> /Contents {cid} 0 R >>"))
        parts.append(_obj(cid,
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"))

    head = "%PDF-1.4\n"
    offsets, pos, body = [], len(head), ""
    for part in parts:
        offsets.append(pos)
        body += part
        pos += len(part)

    count = len(parts) + 1
    xref = f"xref\n0 {count}\n0000000000 65535 f \n" + "".join(
        f"{o:010d} 00000 n \n" for o in offsets
    )
    trailer = f"trailer\n<< /Size {count} /Root 1 0 R >>\nstartxref\n{pos}\n%%EOF\n"
    return (head + body + xref + trailer).encode("latin-1")


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
