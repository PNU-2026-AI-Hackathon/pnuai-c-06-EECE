"""API 키.

## 무엇을 위한 것인가

**웹 화면 없이 검사를 돌리는 길이다.** 요금표의 Pro 가 파는 것이 이것이고,
GitHub 연동(CI)도 결국 이 키로 붙는다.

세션 쿠키로는 안 된다. CI 러너에는 브라우저가 없고, 쿠키는 만료되며,
`SameSite` 때문에 다른 출처에서 실려 가지도 않는다.

## 원문을 저장하지 않는다

**세션 토큰과 같은 규칙이다** (`auth.py` 의 `session_fingerprint`).
DB 에는 SHA-256 만 남기고, 원문은 만들 때 한 번만 사용자에게 보여준다.
DB 가 새도 그 파일만으로는 남의 계정에 못 들어간다.

그래서 **잃어버린 키는 되찾을 수 없다.** 새로 만들어야 한다 —
화면이 그 사실을 만들 때 미리 말한다 (헌법 2-4).

## 접두어를 붙이는 이유

`prefab_` 로 시작하게 만든다. GitHub 의 비밀키 스캔이나 사람 눈이
**저장소에 실수로 커밋된 키를 알아볼 수 있어야** 한다. 접두어가 없으면
그냥 무작위 문자열이라 아무도 못 알아본다.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

#: 키 앞에 붙는 표식. **바꾸지 않는다** — 이미 발급된 키가 안 맞게 된다.
PREFIX = "prefab_"

#: 무작위 부분의 바이트 수. 32바이트면 64자리 16진수다.
#: 세션 토큰과 같은 강도이고, 이 값이 곧 계정 접근 권한이라 줄일 이유가 없다.
TOKEN_BYTES = 32

#: 한 사람이 가질 수 있는 키 수.
#:
#: **왜 상한을 두는가.** 키는 지우기보다 만들기가 쉬워서 방치되기 쉽고,
#: 살아 있는 키가 많을수록 하나가 새는 날 피해가 커진다. 다섯이면
#: 개발용·CI용·예비를 두고도 남는다.
MAX_KEYS_PER_USER = 5

#: 이름 길이. 사람이 "어디에 쓰는 키인지" 적는 칸이라 짧아도 된다.
MAX_LABEL_LEN = 60

_LABEL = re.compile(r"^[^\x00-\x1f]{1,%d}$" % MAX_LABEL_LEN)


class ApiKeyError(ValueError):
    """사용자에게 그대로 보여줄 수 있는 거절 사유."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    label        TEXT NOT NULL,
    fingerprint  TEXT NOT NULL UNIQUE,
    created_at   TEXT NOT NULL,
    last_used_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys (user_id, created_at);
"""


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def fingerprint(token: str) -> str:
    """DB 에 남기는 값. **원문은 어디에도 저장하지 않는다.**"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return PREFIX + secrets.token_hex(TOKEN_BYTES)


def looks_like_key(raw: str | None) -> bool:
    """접두어만 보고 「키를 주려던 것」인지 가른다.

    **틀린 키와 아예 안 준 것을 구분하기 위해서다.** 헤더에 아무것도 없으면
    쿠키로 넘어가면 되지만, `prefab_` 로 시작하는 무언가를 줬는데 안 맞으면
    그건 알려줘야 하는 실패다 — 사용자는 키가 맞는 줄 알고 있다.
    """
    return bool(raw and raw.startswith(PREFIX))


@dataclass(frozen=True)
class ApiKey:
    """목록에 보여줄 정보. **원문은 여기 없다.**"""

    id: str
    label: str
    created_at: str
    last_used_at: str | None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create(conn: sqlite3.Connection, user_id: str, label: str) -> tuple[ApiKey, str]:
    """키를 만든다. 돌려주는 원문은 **이때 한 번만** 존재한다."""
    clean = (label or "").strip()
    if not _LABEL.match(clean):
        raise ApiKeyError(
            "BAD_LABEL", f"키 이름을 1~{MAX_LABEL_LEN}자로 적어 주세요. 어디에 쓰는 키인지 적으면 나중에 찾기 쉽습니다."
        )

    count = conn.execute("SELECT COUNT(*) FROM api_keys WHERE user_id = ?", (user_id,)).fetchone()[0]
    if count >= MAX_KEYS_PER_USER:
        raise ApiKeyError(
            "TOO_MANY_KEYS",
            f"키는 {MAX_KEYS_PER_USER}개까지 만들 수 있습니다. 안 쓰는 키를 먼저 지워 주세요.",
        )

    token = new_token()
    key = ApiKey(id=secrets.token_hex(8), label=clean, created_at=_now(), last_used_at=None)
    conn.execute(
        "INSERT INTO api_keys (id, user_id, label, fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
        (key.id, user_id, key.label, fingerprint(token), key.created_at),
    )
    conn.commit()
    return key, token


def list_for(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT id, label, created_at, last_used_at FROM api_keys "
        "WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [
        ApiKey(id=r[0], label=r[1], created_at=r[2], last_used_at=r[3]).to_dict() for r in rows
    ]


def revoke(conn: sqlite3.Connection, user_id: str, key_id: str) -> bool:
    """지운다. 남의 키는 못 지운다. 지웠으면 `True`."""
    cur = conn.execute("DELETE FROM api_keys WHERE id = ? AND user_id = ?", (key_id, user_id))
    conn.commit()
    return cur.rowcount > 0


def user_for(conn: sqlite3.Connection, token: str | None) -> str | None:
    """키로 사용자를 찾는다. 없으면 `None`.

    **마지막 사용 시각을 남긴다.** 사용자가 「이 키 아직 쓰이나?」를 알아야
    안 쓰는 키를 지울 수 있다. 안 남기면 무서워서 아무도 못 지운다.
    """
    if not looks_like_key(token):
        return None
    row = conn.execute(
        "SELECT id, user_id FROM api_keys WHERE fingerprint = ?", (fingerprint(token or ""),)
    ).fetchone()
    if row is None:
        return None
    conn.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (_now(), row[0]))
    conn.commit()
    return row[1]
