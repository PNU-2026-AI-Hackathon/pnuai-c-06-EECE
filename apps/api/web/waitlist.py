"""출시 알림 대기 명단 — **결제를 만들기 전에 살 사람이 있는지 재는 자리.**

요금표가 「준비 중」이라고만 적혀 있는 동안은 방문자가 반응할 대상이 없다.
비싼지 싼지, 살 만한지 아닌지 아무도 말해 주지 않는다. 그래서 가격을 숫자로 공개하고
**여기에 이메일을 남길 수 있게** 한다. 결제 시스템 없이 수요를 재는 가장 싼 방법이다.

## 지키는 것

- **이메일 하나만 받는다.** 이름·소속·전화번호를 받지 않는다. 물어볼 이유가 없다
- **약속을 지킬 수 있는 만큼만 한다.** 우리는 아직 메일 발송 수단이 없다.
  그래서 화면 문구는 "준비되면 이 주소로 알려드립니다" 까지이고,
  광고 메일이나 뉴스레터를 보내겠다고 말하지 않는다
- **같은 주소를 여러 번 넣어도 한 줄이다.** 대기 명단 수가 곧 수요 신호인데
  중복이 섞이면 그 숫자가 거짓말이 된다
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone

#: 받을 수 있는 요금제 이름. **여기 없는 값은 거절한다** —
#: 프론트가 오타를 내면 조용히 저장되고, 나중에 집계가 틀린다.
PLANS = ("pro", "team")

#: 이메일 모양 검사. 엄격하게 하지 않는다 — RFC 를 그대로 구현하면 멀쩡한 주소를 막는다.
#: 우리가 막으려는 것은 오타가 아니라 **주소가 아닌 값**이다.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

#: 이메일 길이 상한. DB 를 채우는 장난을 막는 최소한의 선.
MAX_EMAIL_LEN = 254


class WaitlistError(ValueError):
    """사용자에게 그대로 보여줄 수 있는 거절 사유."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def normalize_email(raw: str) -> str:
    """앞뒤 공백을 떼고 소문자로. **대소문자만 다른 주소를 다른 사람으로 세지 않는다.**"""
    return (raw or "").strip().lower()


def validate(email: str, plan: str) -> tuple[str, str]:
    """저장해도 되는 값인지 본다. 아니면 이유를 들고 거절한다."""
    email = normalize_email(email)
    if not email:
        raise WaitlistError("EMAIL_REQUIRED", "이메일 주소를 입력해 주세요.")
    if len(email) > MAX_EMAIL_LEN:
        raise WaitlistError("EMAIL_TOO_LONG", "이메일 주소가 너무 깁니다.")
    if not _EMAIL.match(email):
        raise WaitlistError("EMAIL_INVALID", "이메일 주소 형태가 아닙니다. 다시 확인해 주세요.")
    if plan not in PLANS:
        raise WaitlistError("PLAN_UNKNOWN", "알 수 없는 요금제입니다.")
    return email, plan


def init(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS waitlist (
            email      TEXT NOT NULL,
            plan       TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (email, plan)
        )
        """
    )


def join(conn: sqlite3.Connection, email: str, plan: str) -> None:
    """대기 명단에 넣는다. **이미 있으면 조용히 성공이다.**

    "이미 등록하셨습니다" 는 사용자에게 아무 쓸모가 없고, 오히려 이 주소가
    이미 명단에 있다는 사실을 아무에게나 알려주는 셈이 된다.
    """
    email, plan = validate(email, plan)
    conn.execute(
        "INSERT OR IGNORE INTO waitlist (email, plan, created_at) VALUES (?, ?, ?)",
        (email, plan, datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")),
    )


def count(conn: sqlite3.Connection, plan: str | None = None) -> int:
    """대기 인원. 요금제를 주면 그 요금제만 센다."""
    if plan is None:
        row = conn.execute("SELECT COUNT(*) FROM waitlist").fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) FROM waitlist WHERE plan = ?", (plan,)).fetchone()
    return int(row[0]) if row else 0
