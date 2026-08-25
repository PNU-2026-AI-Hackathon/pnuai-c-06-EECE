"""데이터시트 읽기 요청 할당량.

## 왜 검사가 아니라 여기를 끊는가

**판정은 원가가 0이다.** 규칙은 순수 함수라 네트워크도 LLM 도 안 쓴다.
같은 사람이 하루에 천 번 검사해도 우리 돈은 한 푼도 안 나간다.
그래서 **검사 횟수를 제한하면 엉뚱한 것을 제한하는 것**이고, 우리가 경쟁 제품에
없는 「검사 무제한 무료」를 스스로 버리는 일이다.

돈이 나가는 자리는 하나다 — **아직 안 읽은 부품의 데이터시트를 LLM 으로 읽을 때.**
실측 약 $0.03/부품 (`CLAUDE.md` 「실제 LLM 호출」 절).

## 원가가 「검사당」이 아니라 「부품당」이다

한 번 읽은 부품은 **모든 사용자가 쓴다** (`part_facts` 는 공용이다).
그래서 같은 부품에 대한 두 번째 요청부터는 원가가 0이고, DB 가 찰수록
요청 자체가 준다. **이미 읽은 부품은 할당량을 세지 않는다** — 그게 이 모듈의 핵심이다.

## 무료에도 왜 주는가

무료 사용자의 요청이 **우리 자산을 키운다.** 완전히 막으면 부품 DB 가 안 큰다.
소량을 열어 두는 편이 우리에게 이득이다.
"""

from __future__ import annotations

import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

#: 요금제별 **한 달** 새 부품 읽기 요청 한도.
#:
#: 실측 $0.03/부품 기준으로 무료는 월 $0.09, Pro 는 $0.90 이다.
#: Pro 가 9,900원(약 $7)이라 여유가 크다 — 한도를 빡빡하게 잡을 이유가 없다.
MONTHLY_LIMIT: dict[str, int] = {
    "free": 3,
    "pro": 30,
    "team": 200,
}

DEFAULT_PLAN = "free"

#: 부품번호 표기. 대소문자·하이픈·언더바·슬래시까지 받는다.
#: 사람이 BOM 에서 복사해 붙이는 값이라 넉넉하게 받고 **저장할 때 정규화**한다.
_MPN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/+-]{1,63}$")


class QuotaError(ValueError):
    """사용자에게 그대로 보여줄 수 있는 거절 사유."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def normalize_mpn(raw: str) -> str:
    """`  esp32-c6  ` → `ESP32-C6`. 대소문자만 다른 요청을 같은 부품으로 센다."""
    return (raw or "").strip().upper()


def limit_for(plan: str | None) -> int:
    """모르는 요금제는 무료로 본다. **없는 요금제에 큰 한도를 주지 않는다.**"""
    return MONTHLY_LIMIT.get(plan or DEFAULT_PLAN, MONTHLY_LIMIT[DEFAULT_PLAN])


def month_of(when: datetime) -> str:
    """`2026-08`. 달이 바뀌면 저절로 초기화된다 — 지우는 작업이 필요 없다."""
    return when.astimezone(timezone.utc).strftime("%Y-%m")


@dataclass(frozen=True)
class Quota:
    """지금 이 사람이 이번 달에 쓸 수 있는 양."""

    plan: str
    limit: int
    used: int

    @property
    def left(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def exhausted(self) -> bool:
        return self.left <= 0

    def to_dict(self) -> dict:
        return {"plan": self.plan, "limit": self.limit, "used": self.used, "left": self.left}


SCHEMA = """
CREATE TABLE IF NOT EXISTS datasheet_requests (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    mpn        TEXT NOT NULL,
    month      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'pending'
);
CREATE INDEX IF NOT EXISTS idx_req_user_month ON datasheet_requests (user_id, month);
CREATE UNIQUE INDEX IF NOT EXISTS idx_req_user_mpn ON datasheet_requests (user_id, mpn);
"""


def init(conn: sqlite3.Connection) -> None:
    """요청 표를 만들고, 오래된 DB 라면 `users.plan` 을 이주시킨다."""
    conn.executescript(SCHEMA)
    _migrate_plan_column(conn)
    conn.commit()


def _migrate_plan_column(conn: sqlite3.Connection) -> None:
    """이미 만들어진 DB 의 `users` 에 `plan` 을 붙인다.

    **새 DB 는 이 함수가 할 일이 없다** — `auth.py` 의 `CREATE TABLE users` 가
    이미 칼럼을 갖고 있다. 여기는 8/26 이전에 만들어진 DB 를 위한 이주다.

    `users` 표가 아직 없을 수 있다. `service.Store` 가 `AuthStore` 보다 먼저
    도는 배포 순서가 있어서다 — 그때는 그냥 넘어간다. 다음 기동에는 표가 있고,
    없더라도 `auth.py` 스키마가 칼럼을 들고 있으므로 결과가 같다.

    **모르는 오류까지 삼키지 않는다.** 스키마가 틀어진 것을 못 알아채면
    화면이 잘못된 한도를 보여주고도 조용하다.
    """
    try:
        conn.execute(f"ALTER TABLE users ADD COLUMN plan TEXT NOT NULL DEFAULT '{DEFAULT_PLAN}'")
    except sqlite3.OperationalError as exc:
        reason = str(exc).lower()
        if "duplicate column" not in reason and "no such table" not in reason:
            raise


def plan_of(conn: sqlite3.Connection, user_id: str) -> str:
    row = conn.execute("SELECT plan FROM users WHERE id = ?", (user_id,)).fetchone()
    return (row[0] if row and row[0] else DEFAULT_PLAN)


def quota_of(conn: sqlite3.Connection, user_id: str, *, now: datetime | None = None) -> Quota:
    """이번 달 남은 요청 수. **화면이 미리 보여줄 수 있어야** 하므로 따로 뺐다."""
    when = now or datetime.now(timezone.utc)
    plan = plan_of(conn, user_id)
    used = conn.execute(
        "SELECT COUNT(*) FROM datasheet_requests WHERE user_id = ? AND month = ?",
        (user_id, month_of(when)),
    ).fetchone()[0]
    return Quota(plan=plan, limit=limit_for(plan), used=used)


def already_known(conn: sqlite3.Connection, mpn: str) -> bool:
    """이미 읽은 부품인가. **이러면 할당량을 안 쓴다.**

    `part_facts` 가 없는 배포(사실 DB 를 안 심은 경우)에서도 요청은 되어야 하므로
    표가 없으면 「모른다」로 본다.
    """
    try:
        row = conn.execute(
            "SELECT 1 FROM part_facts WHERE UPPER(mpn) = ? LIMIT 1", (normalize_mpn(mpn),)
        ).fetchone()
    except sqlite3.OperationalError:
        return False
    return row is not None


def request(
    conn: sqlite3.Connection,
    user_id: str,
    raw_mpn: str,
    *,
    now: datetime | None = None,
) -> dict:
    """읽기 요청을 남긴다. 실패는 `QuotaError` 로만 알린다.

    **이미 읽은 부품은 할당량을 안 쓰고 그 자리에서 알려준다.** 원가가 0이라서다.
    같은 사람이 같은 부품을 두 번 요청해도 한 번만 센다 (유니크 인덱스).
    """
    when = now or datetime.now(timezone.utc)
    mpn = normalize_mpn(raw_mpn)
    if not _MPN.match(mpn):
        raise QuotaError("BAD_MPN", "부품번호 형식이 아닙니다. BOM 에 적힌 값을 그대로 넣어 주세요.")

    if already_known(conn, mpn):
        return {"status": "known", "mpn": mpn, "quota": quota_of(conn, user_id, now=when).to_dict()}

    existing = conn.execute(
        "SELECT status FROM datasheet_requests WHERE user_id = ? AND mpn = ?", (user_id, mpn)
    ).fetchone()
    if existing is not None:
        return {
            "status": "already_requested",
            "mpn": mpn,
            "quota": quota_of(conn, user_id, now=when).to_dict(),
        }

    quota = quota_of(conn, user_id, now=when)
    if quota.exhausted:
        raise QuotaError(
            "QUOTA_EXHAUSTED",
            f"이번 달 데이터시트 읽기 요청을 다 쓰셨습니다 ({quota.limit}건). "
            "다음 달에 다시 열립니다.",
        )

    conn.execute(
        "INSERT INTO datasheet_requests (id, user_id, mpn, month, created_at, status) "
        "VALUES (?, ?, ?, ?, ?, 'pending')",
        (secrets.token_hex(8), user_id, mpn, month_of(when), when.isoformat()),
    )
    conn.commit()
    return {
        "status": "queued",
        "mpn": mpn,
        "quota": quota_of(conn, user_id, now=when).to_dict(),
    }


def pending(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    """처리 대기 중인 요청. **사람이 보고 데이터시트를 읽는다** (헌법 2-1).

    자동으로 LLM 을 부르지 않는다. 추출 결과는 `parts/*.json` 으로 나오고
    사람이 확인한 뒤 커밋한다.
    """
    rows = conn.execute(
        "SELECT mpn, COUNT(*) AS n, MIN(created_at) AS first_at FROM datasheet_requests "
        "WHERE status = 'pending' GROUP BY mpn ORDER BY n DESC, first_at ASC LIMIT ?",
        (limit,),
    ).fetchall()
    return [{"mpn": r[0], "requests": r[1], "first_requested_at": r[2]} for r in rows]
