"""데이터시트 축 — BOM 으로 부품을 식별하고, 그 부품의 사실을 읽어 온다.

지금 있는 것: BOM CSV 파서 (B-1).
아직 없는 것: 데이터시트 PDF 확보(B-2) · LLM 사실 추출(B-3) · 부품 사실 DB(B-4).

LLM 은 **비정형 문서를 읽는 데만** 쓴다. 판정은 코드가 한다 (CLAUDE.md 2-1).
"""

from .bom import Bom, BomEntry, BomParseError, SkippedRow, parse, parse_text

__all__ = ["Bom", "BomEntry", "BomParseError", "SkippedRow", "parse", "parse_text"]
