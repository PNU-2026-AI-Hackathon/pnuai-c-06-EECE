"""계정과 세션.

**여기서 잘못 만든 것은 조용히 틀리지 않는다 — 남의 비밀번호가 샌다.**
그래서 이 파일은 다른 파일들보다 보수적이다. 편의를 위해 타협한 자리가 없다.

## 고른 것과 고르지 않은 것

- **`hashlib.scrypt`.** 표준 라이브러리다. bcrypt·argon2 를 깔지 않은 이유는
  의존성을 줄이려는 게 아니라, **깔았는데 배포 이미지에서 빠지는 사고**가
  이 층에서 나면 로그인이 통째로 멈추기 때문이다. scrypt 는 파이썬이 있으면 있다.
- **평문 비교를 하지 않는다.** `hmac.compare_digest` 로 상수 시간에 비교한다.
  `==` 로 비교하면 앞자리부터 맞는 만큼 시간이 더 걸려서, 그 차이로 값을 맞힐 수 있다.
- **세션 토큰은 DB 에 해시로 넣는다.** DB 가 새어도 그걸로 로그인할 수 없어야 한다.
  토큰은 무작위라 사전 공격이 안 통하므로 여기서는 SHA-256 으로 충분하다 —
  비밀번호와 달리 느리게 만들 이유가 없다.

## 안 만든 것 (헌법 2-4)

- **비밀번호 재설정.** 메일 보낼 수단이 없다. 잊으면 그 계정은 끝이다.
  화면에 그렇게 적는다. 있는 척하는 것보다 없다고 말하는 게 낫다.
- **메일 인증.** 같은 이유다. 그래서 이메일은 **신원 확인 수단이 아니라
  그냥 이름표**다. 남의 주소로도 가입된다.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

#: scrypt 매개변수. **OWASP 권고치(N=2^17)보다 낮춰 잡았다. 이유를 적는다.**
#:
#: scrypt 는 일부러 메모리를 많이 쓴다. 필요한 양이 `128 * N * r` 바이트라서
#: N 을 올리면 시간과 메모리가 **같이** 오른다. 재 봤다.
#:
#:     N=2^14   16MB    37ms
#:     N=2^15   32MB    74ms
#:     N=2^16   64MB   146ms
#:     N=2^17  128MB   292ms      ← OWASP 권고치
#:
#: 배포 컨테이너는 무료 플랜이라 메모리가 512MB 다. 2^17 이면 **로그인 한 번에
#: 128MB** 를 잡고, 동시에 서너 개만 들어와도 프로세스가 죽는다. 비밀번호를
#: 지키려고 고른 값이 서비스를 눕히는 수단이 되는 것이다.
#:
#: 2^15 로 간다. 32MB · 74ms — 무차별 대입에는 여전히 벽이고(초당 13번),
#: 그 위에 **로그인 시도 자체에 요청 제한**을 건다. 벽을 하나만 세우지 않는다.
#:
#: **유료 플랜으로 올려 메모리가 늘면 이 값을 2^17 로 올린다.** 해시 문자열에
#: N 을 같이 저장하므로 옛 비밀번호도 그대로 검증된다.
SCRYPT_N = 1 << 15
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
SALT_BYTES = 16

#: `maxmem` 을 안 주면 기본값이 작아서 위 매개변수로는 터진다.
#: 대략 128 * N * r * p 바이트가 필요하다 — 여유를 둔다.
SCRYPT_MAXMEM = 128 * SCRYPT_N * SCRYPT_R * SCRYPT_P * 2

SESSION_TOKEN_BYTES = 32
SESSION_DAYS = 30

#: 비밀번호 최소 길이.
#:
#: 대문자·숫자·특수문자를 섞으라고 요구하지 않는다. 그 규칙은 사람을
#: `Password1!` 로 몰아넣을 뿐이고, 길이가 훨씬 세다.
MIN_PASSWORD_LENGTH = 10

#: 이메일은 **형식만** 본다. 실제로 받는 주소인지는 확인할 방법이 없다.
#: 정규식으로 RFC 를 흉내 내려 들지 않는다 — 그 길로 가면 멀쩡한 주소를 막는다.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MAX_EMAIL_LENGTH = 254
MAX_PASSWORD_LENGTH = 1024


class AuthError(Exception):
    """인증 층의 거절. `code` 는 API 오류 코드와 그대로 맞춘다."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass(frozen=True)
class User:
    id: str
    email: str
    created_at: str


# ------------------------------------------------------------ 비밀번호

def hash_password(password: str) -> str:
    """`scrypt$N$r$p$salt$hash` 꼴로 만든다.

    **매개변수를 문자열에 같이 넣는다.** 나중에 N 을 올리면 예전 해시는
    옛 N 으로 검증해야 하는데, 값만 저장해 두면 그때 전부 못 읽게 된다.
    """
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """맞으면 True. **어떤 경우에도 예외를 밖으로 내보내지 않는다.**

    저장된 값이 깨졌을 때 예외가 나가면 500 이 되고, 그 500 자체가
    "이 계정은 뭔가 다르다"는 신호가 된다.
    """
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = _scrypt(password, bytes.fromhex(salt_hex), int(n), int(r), int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=SCRYPT_DKLEN,
        maxmem=128 * n * r * p * 2,
    )


# ---------------------------------------------------------------- 검증

def normalize_email(raw: str) -> str:
    """앞뒤 공백을 떼고 소문자로 만든다.

    `Kim@x.com` 으로 가입하고 `kim@x.com` 으로 로그인하면 안 된다는 말을
    듣게 된다. 사람은 대소문자를 안 세고 친다.
    """
    return raw.strip().lower()


def validate_credentials(email: str, password: str) -> None:
    """가입 때만 부른다. **로그인 때는 부르지 않는다.**

    로그인에서 형식 검사를 하면 "형식이 틀렸다"와 "비밀번호가 틀렸다"가
    다른 응답으로 나가고, 그 차이로 가입된 주소를 알아낼 수 있다.
    """
    if not email or not _EMAIL.match(email):
        raise AuthError("INVALID_EMAIL", "이메일 주소 형식이 아닙니다.", 422)
    if len(email) > MAX_EMAIL_LENGTH:
        raise AuthError("INVALID_EMAIL", "이메일 주소가 너무 깁니다.", 422)
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(
            "WEAK_PASSWORD",
            f"비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다. "
            "길수록 강합니다 — 기억하기 쉬운 문장을 쓰셔도 됩니다.",
            422,
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        # scrypt 는 입력 길이에 비례해 느려진다. 상한이 없으면 긴 비밀번호
        # 하나로 워커를 붙잡을 수 있다.
        raise AuthError("WEAK_PASSWORD", "비밀번호가 너무 깁니다.", 422)


# -------------------------------------------------------------- 세션

def new_session_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def session_fingerprint(token: str) -> str:
    """DB 에 넣을 값. **원본 토큰은 저장하지 않는다.**"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.isoformat()


# --------------------------------------------------------------- 저장

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    fingerprint TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions (user_id);
"""


class AuthStore:
    """계정·세션 저장. **checks 와 같은 SQLite 파일을 쓴다** (헌법 9절)."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        with self._session() as conn:
            conn.executescript(_SCHEMA)

    def _session(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # -- 계정 --------------------------------------------------------

    def create_user(self, email: str, password: str) -> User:
        validate_credentials(email, password)
        user = User(
            id="usr_" + secrets.token_hex(16),
            email=email,
            created_at=_iso(_now()),
        )
        with self._session() as conn:
            try:
                conn.execute(
                    "INSERT INTO users (id, email, password_hash, created_at)"
                    " VALUES (?, ?, ?, ?)",
                    (user.id, user.email, hash_password(password), user.created_at),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                raise AuthError(
                    "EMAIL_TAKEN",
                    "이미 가입된 이메일입니다. 로그인해 주세요.",
                    409,
                ) from None
        return user

    def authenticate(self, email: str, password: str) -> User:
        """맞으면 사용자, 아니면 `AuthError`.

        **없는 계정과 틀린 비밀번호를 구분해서 알리지 않는다.** 구분하면
        어떤 주소가 가입돼 있는지 목록을 만들 수 있다.

        없는 계정일 때도 해시를 한 번 돌린다. 안 돌리면 **없는 계정이 눈에
        띄게 빨리 답하고**, 그 시간 차이가 곧 답이 된다.
        """
        with self._session() as conn:
            row = conn.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
                (email,),
            ).fetchone()

        if row is None:
            hash_password(password)
            raise _bad_credentials()
        if not verify_password(password, row["password_hash"]):
            raise _bad_credentials()
        return User(id=row["id"], email=row["email"], created_at=row["created_at"])

    def find_user(self, user_id: str) -> User | None:
        with self._session() as conn:
            row = conn.execute(
                "SELECT id, email, created_at FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        if row is None:
            return None
        return User(id=row["id"], email=row["email"], created_at=row["created_at"])

    # -- 세션 --------------------------------------------------------

    def open_session(self, user_id: str) -> tuple[str, datetime]:
        """새 세션. 돌려주는 토큰은 **이때 한 번만** 존재한다."""
        token = new_session_token()
        expires = _now() + timedelta(days=SESSION_DAYS)
        with self._session() as conn:
            conn.execute(
                "INSERT INTO sessions (fingerprint, user_id, created_at, expires_at)"
                " VALUES (?, ?, ?, ?)",
                (session_fingerprint(token), user_id, _iso(_now()), _iso(expires)),
            )
            conn.commit()
        return token, expires

    def user_for_token(self, token: str | None) -> User | None:
        """토큰으로 사용자를 찾는다. 없거나 만료면 `None`."""
        if not token:
            return None
        with self._session() as conn:
            row = conn.execute(
                "SELECT user_id, expires_at FROM sessions WHERE fingerprint = ?",
                (session_fingerprint(token),),
            ).fetchone()
            if row is None:
                return None
            if _expired(row["expires_at"]):
                # 만료된 줄을 그때그때 치운다. 따로 청소하는 일을 만들지 않는다.
                conn.execute(
                    "DELETE FROM sessions WHERE fingerprint = ?",
                    (session_fingerprint(token),),
                )
                conn.commit()
                return None
        return self.find_user(row["user_id"])

    def close_session(self, token: str | None) -> None:
        if not token:
            return
        with self._session() as conn:
            conn.execute(
                "DELETE FROM sessions WHERE fingerprint = ?", (session_fingerprint(token),)
            )
            conn.commit()

    def count_users(self) -> int:
        with self._session() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])


def _bad_credentials() -> AuthError:
    return AuthError(
        "BAD_CREDENTIALS", "이메일 또는 비밀번호가 맞지 않습니다.", 401
    )


def _expired(raw: str) -> bool:
    try:
        return datetime.fromisoformat(raw) <= _now()
    except ValueError:
        # 읽을 수 없는 만료 시각은 **만료로 친다.** 반대로 두면 깨진 줄 하나가
        # 영원히 사는 세션이 된다.
        return True
