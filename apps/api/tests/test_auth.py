"""계정과 세션.

**이 층에서 조용히 틀리면 남의 비밀번호가 샌다.** 그래서 여기 테스트는
"되는지"보다 **"새지 않는지"** 를 더 많이 본다.
"""

from __future__ import annotations

import sqlite3

import pytest

from web import auth
from web.auth import AuthError, AuthStore

GOOD = "correct horse battery staple"


@pytest.fixture()
def store(tmp_path):
    return AuthStore(str(tmp_path / "auth.db"))


# ── 비밀번호 ────────────────────────────────────────────────────────

def test_같은_비밀번호도_해시가_매번_다르다():
    """소금이 없으면 **같은 비밀번호를 쓴 계정이 한눈에 보인다.**"""
    assert auth.hash_password(GOOD) != auth.hash_password(GOOD)


def test_해시에_평문이_들어_있지_않다():
    assert GOOD not in auth.hash_password(GOOD)


def test_맞는_비밀번호와_틀린_비밀번호를_가른다():
    stored = auth.hash_password(GOOD)
    assert auth.verify_password(GOOD, stored)
    assert not auth.verify_password(GOOD + " ", stored)
    assert not auth.verify_password("", stored)


def test_저장값이_깨져도_예외가_아니라_False_다():
    """예외가 나가면 500 이 되고, **그 500 자체가 신호**가 된다."""
    for broken in ("", "garbage", "scrypt$$$$$", "bcrypt$1$2$3$4$5", "scrypt$a$b$c$d$e"):
        assert auth.verify_password(GOOD, broken) is False


def test_해시_문자열에_매개변수가_같이_들어_있다():
    """나중에 N 을 올려도 **예전 비밀번호가 그대로 검증돼야** 한다."""
    stored = auth.hash_password(GOOD)
    scheme, n, r, p, _salt, _digest = stored.split("$")
    assert scheme == "scrypt"
    assert (int(n), int(r), int(p)) == (auth.SCRYPT_N, auth.SCRYPT_R, auth.SCRYPT_P)


def test_옛_매개변수로_만든_해시도_검증된다(monkeypatch):
    """N 을 올리는 날 로그인이 통째로 멈추면 안 된다."""
    monkeypatch.setattr(auth, "SCRYPT_N", 1 << 14)
    old = auth.hash_password(GOOD)
    monkeypatch.setattr(auth, "SCRYPT_N", 1 << 15)
    assert auth.verify_password(GOOD, old)


def test_메모리를_감당할_수_있는_매개변수다():
    """scrypt 는 `128 * N * r` 바이트를 쓴다. 배포 컨테이너가 512MB 다.

    OWASP 권고치(2^17)면 로그인 한 번에 128MB 라 동시 서너 개에 죽는다.
    **비밀번호를 지키려고 고른 값이 서비스를 눕히는 수단이 되면 안 된다.**
    """
    need_mb = 128 * auth.SCRYPT_N * auth.SCRYPT_R / (1024 * 1024)
    assert need_mb <= 64


# ── 입력 검증 ──────────────────────────────────────────────────────

def test_짧은_비밀번호를_거절한다(store):
    with pytest.raises(AuthError) as caught:
        store.create_user("a@b.com", "짧다")
    assert caught.value.code == "WEAK_PASSWORD"


def test_아주_긴_비밀번호를_거절한다(store):
    """scrypt 는 입력 길이에 비례해 느려진다 — 상한이 없으면 워커를 붙잡는다."""
    with pytest.raises(AuthError):
        store.create_user("a@b.com", "x" * 5000)


def test_이메일_형식을_본다(store):
    for bad in ("", "  ", "kim", "kim@", "@example.com", "kim example@x.com"):
        with pytest.raises(AuthError) as caught:
            store.create_user(bad, GOOD)
        assert caught.value.code == "INVALID_EMAIL"


def test_대소문자와_공백을_흡수한다():
    """`Kim@x.com` 으로 가입하고 `kim@x.com` 으로 로그인하면 안 된다는 말을 듣게 된다."""
    assert auth.normalize_email("  Kim@Example.COM ") == "kim@example.com"


# ── 계정 ────────────────────────────────────────────────────────────

def test_같은_이메일로_두_번_가입할_수_없다(store):
    store.create_user("a@b.com", GOOD)
    with pytest.raises(AuthError) as caught:
        store.create_user("a@b.com", GOOD)
    assert caught.value.status == 409


def test_비밀번호가_평문으로_저장되지_않는다(store, tmp_path):
    """**DB 파일을 통째로 읽어서 확인한다.** 코드를 믿지 않는다."""
    store.create_user("a@b.com", GOOD)
    raw = (tmp_path / "auth.db").read_bytes()
    assert GOOD.encode() not in raw


def test_로그인이_된다(store):
    made = store.create_user("a@b.com", GOOD)
    assert store.authenticate("a@b.com", GOOD).id == made.id


def test_없는_계정과_틀린_비밀번호가_같은_말을_한다(store):
    """구분하면 **어떤 주소가 가입돼 있는지 목록을 만들 수 있다.**"""
    store.create_user("a@b.com", GOOD)
    errors = []
    for email, password in (("a@b.com", "wrong password here"), ("nobody@b.com", GOOD)):
        with pytest.raises(AuthError) as caught:
            store.authenticate(email, password)
        errors.append((caught.value.code, caught.value.message, caught.value.status))
    assert errors[0] == errors[1]


def test_없는_계정도_해시를_한_번_돌린다(store, monkeypatch):
    """안 돌리면 **없는 계정이 눈에 띄게 빨리 답하고**, 그 차이가 곧 답이 된다."""
    calls = []
    original = auth.hash_password
    monkeypatch.setattr(auth, "hash_password", lambda pw: calls.append(pw) or original(pw))
    with pytest.raises(AuthError):
        store.authenticate("nobody@b.com", GOOD)
    assert calls, "없는 계정인데 해시를 건너뛰었다"


# ── 세션 ────────────────────────────────────────────────────────────

def test_세션_토큰이_DB_에_평문으로_없다(store, tmp_path):
    """**DB 가 새어도 그걸로 로그인할 수 없어야 한다.**"""
    user = store.create_user("a@b.com", GOOD)
    token, _ = store.open_session(user.id)
    assert token.encode() not in (tmp_path / "auth.db").read_bytes()


def test_토큰으로_사용자를_찾는다(store):
    user = store.create_user("a@b.com", GOOD)
    token, _ = store.open_session(user.id)
    assert store.user_for_token(token).id == user.id


def test_없는_토큰과_빈_토큰은_None(store):
    assert store.user_for_token(None) is None
    assert store.user_for_token("") is None
    assert store.user_for_token("아무거나") is None


def test_로그아웃하면_토큰이_죽는다(store):
    user = store.create_user("a@b.com", GOOD)
    token, _ = store.open_session(user.id)
    store.close_session(token)
    assert store.user_for_token(token) is None


def test_다른_세션은_로그아웃에_영향을_안_받는다(store):
    """한 기기에서 로그아웃했다고 다른 기기가 튕기면 안 된다."""
    user = store.create_user("a@b.com", GOOD)
    phone, _ = store.open_session(user.id)
    laptop, _ = store.open_session(user.id)
    store.close_session(phone)
    assert store.user_for_token(laptop) is not None


def test_만료된_세션은_안_통하고_치워진다(store, tmp_path):
    user = store.create_user("a@b.com", GOOD)
    token, _ = store.open_session(user.id)
    conn = sqlite3.connect(str(tmp_path / "auth.db"))
    conn.execute(
        "UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00' WHERE fingerprint = ?",
        (auth.session_fingerprint(token),),
    )
    conn.commit()
    conn.close()

    assert store.user_for_token(token) is None

    conn = sqlite3.connect(str(tmp_path / "auth.db"))
    left = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    conn.close()
    assert left == 0, "만료된 줄이 남으면 따로 청소하는 일을 만들게 된다"


def test_읽을_수_없는_만료시각은_만료로_친다(store, tmp_path):
    """반대로 두면 **깨진 줄 하나가 영원히 사는 세션**이 된다."""
    user = store.create_user("a@b.com", GOOD)
    token, _ = store.open_session(user.id)
    conn = sqlite3.connect(str(tmp_path / "auth.db"))
    conn.execute("UPDATE sessions SET expires_at = '언제였더라'")
    conn.commit()
    conn.close()
    assert store.user_for_token(token) is None
