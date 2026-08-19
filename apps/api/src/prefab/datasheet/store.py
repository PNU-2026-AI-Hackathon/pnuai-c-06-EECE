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
from dataclasses import dataclass, field as _field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

from .facts import CHIP_INHERITED, CONF_NONE, TIER_MEASURED, TIER_UNOFFICIAL, Fact, FactSet

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

#: 보드 → 칩. BOM 에는 보드 이름이 적히고 데이터시트는 칩 이름으로 나온다.
#: `prefab-datasheet` 스킬이 경고하는 "모듈 vs 칩" 함정을 이 표가 잇는다.
_ALIAS_SCHEMA = """
CREATE TABLE IF NOT EXISTS part_aliases (
    board      TEXT PRIMARY KEY,
    chip       TEXT NOT NULL,
    created_at TEXT NOT NULL
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
            conn.execute(_ALIAS_SCHEMA)

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
        """MPN 목록으로 아는 사실을 전부 꺼낸다. **LLM 을 부르기 전에 이걸 먼저 한다.**

        보드 이름으로 물어도 그 보드가 얹은 칩의 **핀 전기 특성**은 같이 나온다
        (`CHIP_INHERITED`). BOM 에는 보드 이름이 적히고 데이터시트는 칩 이름으로
        나오기 때문이다.
        """
        wanted = [m for m in dict.fromkeys(mpns) if m]
        if not wanted:
            return Lookup(FactSet(), [], [])

        alias = self._aliases(wanted)
        chips = [c for c in dict.fromkeys(alias.values()) if c not in wanted]

        marks = ",".join("?" * len(wanted + chips))
        with self._session() as conn:
            rows = conn.execute(
                f"SELECT * FROM part_facts WHERE mpn IN ({marks})", wanted + chips
            ).fetchall()

        found_facts = [_row_to_fact(r) for r in rows]
        by_mpn: dict[str, dict[str, Fact]] = {}
        for f in found_facts:
            by_mpn.setdefault(f.mpn, {})[f.field] = f

        facts = [f for f in found_facts if f.mpn in wanted]
        for board, chip in alias.items():
            own = by_mpn.get(board, {})
            for field, fact in by_mpn.get(chip, {}).items():
                # 보드가 직접 가진 사실이 칩에서 물려받은 것보다 세다.
                if field in CHIP_INHERITED and field not in own:
                    facts.append(_inherit(fact, board))

        found = {f.mpn for f in facts}
        return Lookup(
            facts=FactSet(facts),
            hits=[m for m in wanted if m in found],
            misses=[m for m in wanted if m not in found],
        )

    def _aliases(self, boards: list[str]) -> dict[str, str]:
        marks = ",".join("?" * len(boards))
        with self._session() as conn:
            rows = conn.execute(
                f"SELECT board, chip FROM part_aliases WHERE board IN ({marks})", boards
            ).fetchall()
        return {r["board"]: r["chip"] for r in rows}

    def alias(self, board: str, chip: str) -> None:
        """보드가 어느 칩을 얹었는지 적어 둔다."""
        if not board or not chip or board == chip:
            return
        with self._session() as conn:
            conn.execute(
                "INSERT INTO part_aliases VALUES (?,?,?) "
                "ON CONFLICT(board) DO UPDATE SET chip=excluded.chip",
                (board, chip, datetime.now(UTC).isoformat(timespec="seconds")),
            )

    # ── 6단계: DB 에 쓴다 ──────────────────────────────────────────────

    def save(self, extraction: dict[str, Any]) -> SaveReport:
        """5단계 JSON 스키마 하나를 저장한다.

        거절 규칙 두 가지다.

        - **값이 있는데 출처가 없으면 거절한다.** 출처 없는 값은 값이 아니다.
          데이터시트면 `page` + `quote`, **실측(`source_tier: measured`)이면 `quote`** 다.
          측정도 출처다 — 쪽 번호 대신 무엇을 어떻게 쟀는지가 그 자리를 채운다.
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

            measured = tier == TIER_MEASURED
            has_source = bool(quote) if measured else bool(page and quote)
            if value is not None and not has_source:
                want = "quote(측정 기록)" if measured else "page·quote"
                report.rejected.append(
                    Rejected(mpn, name, f"값은 있는데 출처({want})가 없다")
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

        for board in extraction.get("applies_to_boards") or []:
            self.alias(str(board).strip(), mpn)

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


def _inherit(fact: Fact, board: str) -> Fact:
    """칩의 사실을 보드 이름으로 다시 붙인다.

    **출처는 그대로 둔다** — 칩 데이터시트에서 읽은 것이 맞고, 화면에도 그렇게
    보여야 한다. 다만 왜 이 보드에 적용되는지를 `reason` 앞에 붙인다.
    """
    note = f"{fact.mpn} 칩의 핀 특성이다. {board} 는 그 칩을 얹었을 뿐이라 같은 값이 적용된다."
    return replace(
        fact,
        mpn=board,
        reason=f"{note} {fact.reason}" if fact.reason else note,
    )


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
