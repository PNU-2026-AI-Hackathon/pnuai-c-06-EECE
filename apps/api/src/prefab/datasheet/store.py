"""부품 사실 DB — SQLite.

**여기가 IO 다.** 규칙 함수는 이 파일을 import 하지 않는다 (CLAUDE.md 2-1).
러너가 조회해서 `Context.datasheet` 에 실어주면, 규칙은 순수한 `FactSet` 만 본다.

`prefab-datasheet` 스킬 1단계(캐시 우선)와 5단계(스키마 강제)를 코드로 굳힌 것이다.
DB 파일은 `checks` 와 **같은 파일**을 쓴다 — SQLite 한 개 (CLAUDE.md 9절).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field as _field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

from .facts import CONF_NONE, TIER_UNOFFICIAL, Fact, FactSet

_SCHEMA = """
CREATE TABLE IF NOT EXISTS part_facts (
    mpn         TEXT    NOT NULL,
    field       TEXT    NOT NULL,
    value_num   REAL,
    value_text  TEXT,
    unit        TEXT,
    table_name  TEXT,
    page        INTEGER,
    quote       TEXT,
    confidence  TEXT    NOT NULL,
    reason      TEXT,
    source_url  TEXT,
    source_tier TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    PRIMARY KEY (mpn, field)
)
"""


@dataclass
class Rejected:
    """받아들이지 않은 사실. **조용히 버리지 않는다** (CLAUDE.md 2-4)."""

    mpn: str
    field: str
    why: str


@dataclass
class SaveReport:
    """무엇이 들어갔고 무엇이 거절됐나."""

    stored: int = 0
    negative: int = 0  #: "찾아봤지만 없더라" — 실패가 아니라 정상 결과다
    rejected: list[Rejected] = _field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.rejected


@dataclass
class Lookup:
    """캐시 조회 결과. `misses` 가 곧 LLM 을 불러야 할 목록이다."""

    facts: FactSet
    hits: list[str]
    misses: list[str]

    @property
    def hit_rate(self) -> float:
        total = len(self.hits) + len(self.misses)
        return len(self.hits) / total if total else 0.0


class FactStore:
    """부품 사실 캐시.

    같은 MPN 을 두 번 조회하지 않는 것이 이 제품의 단위경제다.
    """

    def __init__(self, path: str | Path = "prefab.db") -> None:
        self.path = str(path)
        with self._session() as conn:
            conn.execute(_SCHEMA)

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        """커밋하고 **연결도 닫는다** (`web/service.py` 와 같은 이유)."""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    # ── 1단계: 캐시부터 본다 ────────────────────────────────────────────

    def lookup(self, mpns: Iterable[str]) -> Lookup:
        """MPN 목록으로 아는 사실을 전부 꺼낸다. **LLM 을 부르기 전에 이걸 먼저 한다.**"""
        wanted = [m for m in dict.fromkeys(mpns) if m]
        if not wanted:
            return Lookup(FactSet(), [], [])

        marks = ",".join("?" * len(wanted))
        with self._session() as conn:
            rows = conn.execute(
                f"SELECT * FROM part_facts WHERE mpn IN ({marks})", wanted
            ).fetchall()

        facts = [_row_to_fact(r) for r in rows]
        found = {f.mpn for f in facts}
        return Lookup(
            facts=FactSet(facts),
            hits=[m for m in wanted if m in found],
            misses=[m for m in wanted if m not in found],
        )

    # ── 6단계: DB 에 쓴다 ──────────────────────────────────────────────

    def save(self, extraction: dict[str, Any]) -> SaveReport:
        """5단계 JSON 스키마 하나를 저장한다.

        거절 규칙 두 가지다.

        - **값이 있는데 `page` 나 `quote` 가 없으면 거절한다.** 출처 없는 값은 값이 아니다.
        - **값이 없는데 `reason` 이 없으면 거절한다.** "모른다"는 왜 모르는지까지 말해야 한다.

        `value: null` 자체는 거절 사유가 아니다. 찾아봤지만 없더라는 것도 사실이고,
        저장해 둬야 같은 부품을 두 번 조회하지 않는다.
        """
        mpn = str(extraction.get("mpn") or "").strip()
        if not mpn:
            return SaveReport(rejected=[Rejected("", "", "mpn 이 비어 있다")])

        url = extraction.get("source_url")
        tier = extraction.get("source_tier") or TIER_UNOFFICIAL
        now = datetime.now(UTC).isoformat(timespec="seconds")

        report = SaveReport()
        rows: list[tuple[Any, ...]] = []

        for raw in extraction.get("facts") or []:
            name = str(raw.get("field") or "").strip()
            if not name:
                report.rejected.append(Rejected(mpn, "?", "field 이름이 없다"))
                continue

            value = raw.get("value")
            page = raw.get("page")
            quote = raw.get("quote")
            reason = raw.get("reason")

            if value is not None and not (page and quote):
                report.rejected.append(
                    Rejected(mpn, name, "값은 있는데 출처(page·quote)가 없다")
                )
                continue
            if value is None and not reason:
                report.rejected.append(
                    Rejected(mpn, name, "값이 없는데 왜 없는지(reason)가 없다")
                )
                continue

            num = float(value) if isinstance(value, (int, float)) else None
            text = value if isinstance(value, str) else None

            rows.append(
                (
                    mpn, name, num, text,
                    raw.get("unit"), raw.get("table"), page, quote,
                    raw.get("confidence") or CONF_NONE, reason,
                    url, tier, now,
                )
            )
            if value is None:
                report.negative += 1
            else:
                report.stored += 1

        if rows:
            with self._session() as conn:
                conn.executemany(
                    """
                    INSERT INTO part_facts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(mpn, field) DO UPDATE SET
                        value_num=excluded.value_num, value_text=excluded.value_text,
                        unit=excluded.unit, table_name=excluded.table_name,
                        page=excluded.page, quote=excluded.quote,
                        confidence=excluded.confidence, reason=excluded.reason,
                        source_url=excluded.source_url, source_tier=excluded.source_tier,
                        created_at=excluded.created_at
                    """,
                    rows,
                )
        return report

    def save_json(self, text: str) -> SaveReport:
        """추출기가 뱉은 JSON 문자열 그대로 받는다."""
        return self.save(json.loads(text))

    # ── 지표 ─────────────────────────────────────────────────────────

    def size(self) -> tuple[int, int]:
        """(부품 수, 사실 수). 발표에서 "DB 12 → 13" 으로 보여줄 숫자다."""
        with self._session() as conn:
            row = conn.execute(
                "SELECT COUNT(DISTINCT mpn) AS parts, COUNT(*) AS facts FROM part_facts"
            ).fetchone()
        return int(row["parts"]), int(row["facts"])


def _row_to_fact(row: sqlite3.Row) -> Fact:
    value: float | str | None = row["value_num"]
    if value is None:
        value = row["value_text"]
    return Fact(
        mpn=row["mpn"],
        field=row["field"],
        value=value,
        unit=row["unit"],
        table=row["table_name"],
        page=row["page"],
        quote=row["quote"],
        confidence=row["confidence"],
        reason=row["reason"],
        source_url=row["source_url"],
        source_tier=row["source_tier"],
    )
