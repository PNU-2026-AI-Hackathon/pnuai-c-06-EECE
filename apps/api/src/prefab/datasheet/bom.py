"""BOM CSV 파서 — 부품 기호 → 부품번호(MPN).

IPC-D-356 에는 MPN 도 부품값도 제조사도 없다. 그래서 넷리스트만으로는
"K1 이 어떤 릴레이인지"를 알 수 없고, 모르면 데이터시트를 못 읽고,
데이터시트를 못 읽으면 R11·R12 의 `UNRESOLVED` 가 영원히 안 풀린다.

이 모듈은 **읽기만 한다.** 판정도 추측도 하지 않는다.
열 이름이 도구마다 달라서(Flux · KiCad · Altium) 별칭 표로 흡수한다.
읽지 못한 행은 버리지 않고 사유와 함께 들고 다닌다.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

#: 열 이름 별칭. 도구마다 다르게 부른다. 전부 소문자·공백 제거 후 비교한다.
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "ref": (
        "reference", "references", "refdes", "designator", "designators",
        "ref", "refs", "part reference", "기호",
    ),
    "mpn": (
        "mpn", "manufacturerpartnumber", "manufacturer part number", "partnumber",
        "part number", "mfrpartnumber", "mfr. part #", "부품번호",
    ),
    "manufacturer": ("manufacturer", "mfr", "mfg", "brand", "제조사"),
    "value": ("value", "val", "부품값", "값"),
    "footprint": ("footprint", "package", "패키지"),
}

#: 한 칸에 여러 기호가 들어오는 구분자 — `R1, R2, R3` · `R1;R2`
_REF_SPLIT = re.compile(r"[,;/\s]+")

#: `R1-R3` 처럼 범위로 적는 도구가 있다. 확장하지 않고 그대로 둔다 —
#: 잘못 펼치면 없는 부품을 만들어낸다. 사유를 남기고 넘긴다.
_REF_RANGE = re.compile(r"^[A-Za-z]+\d+\s*-\s*[A-Za-z]+?\d+$")

_VALID_REF = re.compile(r"^[A-Za-z]+\d+[A-Za-z]?$")


class BomParseError(ValueError):
    """BOM 으로 읽을 수 없는 파일."""


@dataclass(frozen=True)
class BomEntry:
    """부품 하나."""

    ref: str
    mpn: str | None = None
    manufacturer: str | None = None
    value: str | None = None
    footprint: str | None = None

    @property
    def identified(self) -> bool:
        """데이터시트를 찾아갈 수 있는가. MPN 이 없으면 못 간다."""
        return bool(self.mpn)


@dataclass(frozen=True)
class SkippedRow:
    """읽지 못한 행. 조용히 버리지 않는다."""

    line: int
    raw: str
    reason: str


class Bom:
    """BOM 전체. 기호로 찾는다."""

    def __init__(
        self,
        entries: "list[BomEntry]",
        skipped: "list[SkippedRow]" = None,
        filename: str = "",
    ) -> None:
        self.entries = entries
        self.skipped = skipped or []
        self.filename = filename
        self._by_ref = {e.ref.upper(): e for e in entries}

    def __len__(self) -> int:
        return len(self.entries)

    def get(self, ref: str) -> BomEntry | None:
        return self._by_ref.get(ref.upper())

    def mpn_of(self, ref: str) -> str | None:
        entry = self.get(ref)
        return entry.mpn if entry else None

    @property
    def identified(self) -> "list[BomEntry]":
        return [e for e in self.entries if e.identified]

    def coverage(self, refs: "list[str] | set[str]") -> "tuple[list[str], list[str]]":
        """(부품번호까지 아는 기호, 모르는 기호). 넷리스트 기준으로 센다."""
        known, unknown = [], []
        for ref in sorted(refs):
            entry = self.get(ref)
            (known if entry and entry.identified else unknown).append(ref)
        return known, unknown

    def notes(self) -> "list[str]":
        """파이프라인 2단계에 그대로 실을 문장."""
        out = []
        if self.skipped:
            reasons: dict[str, int] = {}
            for row in self.skipped:
                reasons[row.reason] = reasons.get(row.reason, 0) + 1
            out.append(
                "읽지 못한 행 "
                + " · ".join(f"{r} {n}줄" for r, n in sorted(reasons.items()))
            )
        missing = [e.ref for e in self.entries if not e.identified]
        if missing:
            out.append(f"부품번호 없는 항목 {len(missing)}개 ({', '.join(missing[:5])}…)")
        return out


def _normalise(name: str) -> str:
    return re.sub(r"[\s_·]+", "", (name or "").strip().lower())


def _map_columns(header: "list[str]") -> "dict[str, int]":
    """열 이름 → 우리가 쓰는 이름. 못 찾은 열은 그냥 없다."""
    lookup: "dict[str, int]" = {}
    for index, raw in enumerate(header):
        norm = _normalise(raw)
        for field, aliases in COLUMN_ALIASES.items():
            if field in lookup:
                continue
            if norm in {_normalise(a) for a in aliases}:
                lookup[field] = index
                break
    return lookup


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def parse_text(text: str, filename: str = "") -> Bom:
    """CSV 본문 → Bom. 구분자는 자동으로 알아낸다 (쉼표 · 세미콜론 · 탭)."""
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    rows = list(csv.reader(io.StringIO(text), dialect))
    rows = [r for r in rows if any((c or "").strip() for c in r)]
    if not rows:
        raise BomParseError("BOM 이 비어 있습니다. 헤더와 부품 행이 있는 CSV 인지 확인해 주세요.")

    columns = _map_columns(rows[0])
    if "ref" not in columns:
        raise BomParseError(
            "부품 기호 열을 찾지 못했습니다. "
            "`Reference` · `Designator` · `RefDes` 중 하나를 헤더에 넣어 주세요. "
            f"지금 헤더: {', '.join(c.strip() for c in rows[0] if c.strip())}"
        )

    entries: "list[BomEntry]" = []
    skipped: "list[SkippedRow]" = []
    seen: set[str] = set()

    def cell(row: "list[str]", field: str) -> str | None:
        index = columns.get(field)
        return _clean(row[index]) if index is not None and index < len(row) else None

    for number, row in enumerate(rows[1:], start=2):
        raw_ref = cell(row, "ref")
        if not raw_ref:
            skipped.append(SkippedRow(number, ",".join(row), "기호 없음"))
            continue

        mpn = cell(row, "mpn")
        for token in (t for t in _REF_SPLIT.split(raw_ref) if t):
            if _REF_RANGE.match(token):
                # R1-R3 을 펼치면 없는 부품을 만들어낼 수 있다. 지어내지 않는다.
                skipped.append(SkippedRow(number, token, "범위 표기 (풀어서 적어 주세요)"))
                continue
            if not _VALID_REF.match(token):
                skipped.append(SkippedRow(number, token, "기호 형식이 아님"))
                continue
            if token.upper() in seen:
                skipped.append(SkippedRow(number, token, "중복 기호"))
                continue
            seen.add(token.upper())
            entries.append(
                BomEntry(
                    ref=token,
                    mpn=mpn,
                    manufacturer=cell(row, "manufacturer"),
                    value=cell(row, "value"),
                    footprint=cell(row, "footprint"),
                )
            )

    if not entries:
        raise BomParseError(
            "부품 행을 한 줄도 읽지 못했습니다. 헤더 아래에 기호가 있는지 확인해 주세요."
        )

    return Bom(entries, skipped, filename)


def parse(path) -> Bom:
    from pathlib import Path

    p = Path(path)
    return parse_text(p.read_text(encoding="utf-8-sig", errors="replace"), filename=p.name)
