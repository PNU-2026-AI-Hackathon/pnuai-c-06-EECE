"""BOM(부품 목록) CSV 파서.

넷리스트에는 **부품번호가 하나도 없다.** 그래서 BOM 이 없으면 부품을 식별할 수 없고,
데이터시트를 찾을 수 없고, 데이터시트 기반 규칙이 전부 `UNRESOLVED` 로 남는다.
이 파서가 트랙 B(데이터시트 축) 전체의 입구다.

CLAUDE.md 2-2 — 모르면 모른다고 한다.
읽다가 버린 줄, 넷리스트와 안 맞는 행, 부품번호가 빈 행을 **전부 기록해서 보고한다.**
"""

from __future__ import annotations

import csv
import io
import re
from collections import OrderedDict
from dataclasses import dataclass, field

#: 도구마다 열 이름이 다르다. 실측·문서에서 모은 별칭.
#: Flux · KiCad · Altium · 엑셀 수기 작성까지 커버한다.
_ALIASES: dict[str, tuple[str, ...]] = {
    "refdes": ("refdes", "reference", "references", "designator", "designators",
               "ref", "part reference", "참조", "부품기호"),
    "mpn": ("mpn", "manufacturer part number", "mfr part number", "part number",
            "partnumber", "mfg part #", "부품번호", "제조사부품번호"),
    "manufacturer": ("manufacturer", "mfr", "mfg", "vendor", "제조사"),
    "value": ("value", "val", "값", "정격"),
}

#: 한 행이 여러 부품을 담는 경우가 흔하다 — "C1,C2,C3" 또는 "C1 C2 C3".
_REF_SPLIT = re.compile(r"[,;/\s]+")

#: 부품번호 뒤에 붙는 주석. "HLK-LD2410C (5V)" · "ESP32 [2개]"
_ANNOTATION = re.compile(r"\s*[\(\[][^)\]]*[\)\]]\s*$")

#: 엑셀이 한국어 윈도우에서 저장하면 CP949 다. UTF-8 만 가정하면 깨진다.
_ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")


class BomParseError(ValueError):
    """BOM 으로 읽을 수 없는 파일."""


@dataclass(frozen=True)
class BomRow:
    refdes: str
    #: 정규화된 부품번호. 비었으면 "행은 있는데 번호가 없다"는 뜻이다.
    mpn: str
    #: 정규화 전 원문. 정규화가 틀렸을 때 되짚을 수 있어야 한다.
    mpn_raw: str
    manufacturer: str | None = None
    value: str | None = None

    @property
    def identified(self) -> bool:
        return bool(self.mpn)


@dataclass
class MatchResult:
    """BOM 과 넷리스트를 맞춰본 결과. 양쪽 방향을 다 본다."""

    identified: list[str] = field(default_factory=list)
    #: 넷리스트에 있는데 BOM 에 행이 없는 부품 → 식별 불가
    missing_in_bom: list[str] = field(default_factory=list)
    #: 넷리스트에 행은 있는데 부품번호가 비어 있는 부품
    blank_mpn: list[str] = field(default_factory=list)
    #: BOM 에는 있는데 넷리스트에 없는 부품 → **BOM 과 회로도가 어긋난다**
    extra_in_bom: list[str] = field(default_factory=list)

    @property
    def identified_count(self) -> int:
        return len(self.identified)


class Bom:
    def __init__(
        self,
        rows: "OrderedDict[str, BomRow]",
        notes: list[str] | None = None,
        encoding: str = "utf-8",
    ) -> None:
        self.rows = rows
        #: 읽으며 버리거나 고친 것. 조용히 넘기지 않는다.
        self.notes = notes or []
        self.encoding = encoding

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def mpns(self) -> list[str]:
        """이 BOM 이 아는 부품번호. 중복을 없애고 정렬한다.

        같은 부품번호를 두 번 조회하지 않는 것이 사실 DB 의 단위경제다.
        """
        return sorted({r.mpn for r in self.rows.values() if r.mpn})

    def mpn_of(self, refdes: str) -> str | None:
        row = self.rows.get(refdes.upper())
        return row.mpn if row and row.mpn else None

    def match(self, netlist_refs: "list[str] | set[str]") -> MatchResult:
        """넷리스트 부품과 맞춰본다. **양쪽 방향을 다 본다.**

        BOM 에만 있는 부품은 BOM 과 회로도가 어긋났다는 뜻이라 그냥 넘기지 않는다.
        """
        want = {r.upper() for r in netlist_refs}
        out = MatchResult()
        for ref in sorted(want):
            row = self.rows.get(ref)
            if row is None:
                out.missing_in_bom.append(ref)
            elif not row.identified:
                out.blank_mpn.append(ref)
            else:
                out.identified.append(ref)
        out.extra_in_bom = sorted(set(self.rows) - want)
        return out

    def parse_notes(self) -> list[str]:
        return list(self.notes)


def normalize_mpn(raw: str) -> str:
    """부품번호를 정리한다. **억지로 맞추지 않는다.**

    하는 것: 공백 정리 · 끝에 붙은 괄호 주석 제거.
    안 하는 것: 메모리 옵션 같은 접미사 추측 제거. 어디까지가 기본 품번인지
    벤더마다 달라서, 잘못 자르면 없는 부품을 찾게 된다. 원문을 함께 보관한다.
    """
    s = " ".join((raw or "").split())
    while True:
        stripped = _ANNOTATION.sub("", s)
        if stripped == s:
            break
        s = stripped
    return s.strip()


def _decode(data: bytes) -> tuple[str, str]:
    for enc in _ENCODINGS:
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8(대체문자)"


def _column_map(header: list[str]) -> dict[str, int]:
    found: dict[str, int] = {}
    for i, cell in enumerate(header):
        key = " ".join((cell or "").strip().lower().split())
        for canon, names in _ALIASES.items():
            if canon not in found and key in names:
                found[canon] = i
    return found


def parse_text(text: str, encoding: str = "utf-8") -> Bom:
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        raise BomParseError("BOM 파일이 비어 있습니다.") from None

    cols = _column_map(header)
    if "refdes" not in cols or "mpn" not in cols:
        raise BomParseError(
            "BOM 에서 부품기호(Reference)와 부품번호(MPN) 열을 찾지 못했습니다. "
            f"읽은 헤더: {', '.join(h for h in header if h) or '(비어 있음)'}"
        )

    rows: "OrderedDict[str, BomRow]" = OrderedDict()
    notes: list[str] = []
    blank = 0
    dupes: list[str] = []

    def cell(row: list[str], key: str) -> str:
        i = cols.get(key)
        return (row[i].strip() if i is not None and i < len(row) else "")

    for lineno, row in enumerate(reader, start=2):
        if not any((c or "").strip() for c in row):
            continue
        refs_raw = cell(row, "refdes")
        if not refs_raw:
            notes.append(f"{lineno}행: 부품기호가 비어 있어 건너뜀")
            continue

        mpn_raw = cell(row, "mpn")
        mpn = normalize_mpn(mpn_raw)
        if not mpn:
            blank += 1

        # 한 행이 여러 부품을 담는 경우 — "C1,C2,C3"
        for ref in (r.strip().upper() for r in _REF_SPLIT.split(refs_raw) if r.strip()):
            if ref in rows:
                dupes.append(ref)
                continue
            rows[ref] = BomRow(
                refdes=ref,
                mpn=mpn,
                mpn_raw=mpn_raw,
                manufacturer=cell(row, "manufacturer") or None,
                value=cell(row, "value") or None,
            )

    if not rows:
        raise BomParseError("BOM 에서 부품을 한 개도 읽지 못했습니다.")

    if blank:
        notes.append(f"부품번호가 빈 행 {blank}개 — 그 부품은 식별되지 않습니다")
    if dupes:
        notes.append(f"중복된 부품기호 {len(dupes)}개 (첫 행만 사용): {', '.join(sorted(set(dupes))[:5])}")
    for canon in ("manufacturer", "value"):
        if canon not in cols:
            notes.append(f"'{canon}' 열이 없습니다 (선택 항목)")

    return Bom(rows=rows, notes=notes, encoding=encoding)


def parse_bytes(data: bytes) -> Bom:
    text, enc = _decode(data)
    bom = parse_text(text, encoding=enc)
    if enc not in ("utf-8", "utf-8-sig"):
        bom.notes.insert(0, f"인코딩을 {enc} 로 읽었습니다 (UTF-8 이 아님)")
    return bom
