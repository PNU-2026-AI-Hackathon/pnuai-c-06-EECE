"""GitHub 으로 로그인.

**이 파일이 지키는 것은 편의가 아니라 계정 탈취다.**

    1. 확인 안 된 이메일로는 남의 계정에 못 붙는다   ← 제일 중요하다
    2. 우리가 만들지 않은 state 는 안 받는다 (CSRF)
    3. 만료된 state 도 안 받는다
    4. github_id 가 이메일보다 세다
    5. GitHub 전용 계정은 비밀번호로 못 연다
    6. 설정이 없으면 기능이 **없다** (있는 척하지 않는다)
    7. `?next=` 로 아무 데나 못 보낸다 (오픈 리다이렉트)
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from web import github


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "500")
    monkeypatch.setenv("AUTH_LIMIT_PER_MINUTE", "500")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "iv1.test")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret-for-test")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "http://testserver/api/v1/auth/github/callback")
    monkeypatch.setenv("WEB_APP_URL", "http://web.test")
    import importlib

    from web import app as app_module

    return importlib.reload(app_module)


SECRET = "secret-for-test"


# ------------------------------------------------------------ state (CSRF)

def test_우리가_만든_state_는_통과한다():
    github.check_state(SECRET, github.new_state(SECRET))


def test_남이_만든_state_는_거절한다():
    """공격자가 자기 계정으로 시작한 흐름을 피해자 브라우저에 떨어뜨리는 것을 막는다."""
    forged = github.new_state("attacker-guessed-this")
    with pytest.raises(github.GithubError):
        github.check_state(SECRET, forged)


def test_만료된_state_는_거절한다():
    old = github.new_state(SECRET, now=int(time.time()) - github.STATE_TTL_SECONDS - 1)
    with pytest.raises(github.GithubError):
        github.check_state(SECRET, old)


@pytest.mark.parametrize("raw", [None, "", "쓰레기", "a.b", "a.b.c", "a.999.deadbeef"])
def test_모양이_틀린_state_는_예외없이_거절한다(raw):
    with pytest.raises(github.GithubError):
        github.check_state(SECRET, raw)


def test_거절_사유를_나눠서_말하지_않는다():
    """위조인지 만료인지 알려 주면 공격자가 어디까지 맞췄는지 알게 된다."""
    forged = github.new_state("wrong-secret")
    expired = github.new_state(SECRET, now=int(time.time()) - 10_000)
    messages = set()
    for raw in (forged, expired, "쓰레기"):
        try:
            github.check_state(SECRET, raw)
        except github.GithubError as failure:
            messages.add((failure.code, failure.message))
    assert len(messages) == 1


# ------------------------------------------------------------ 이메일 고르기

def test_인증된_기본_주소를_고른다():
    assert github.pick_email(
        [
            {"email": "alt@x.com", "primary": False, "verified": True},
            {"email": "me@x.com", "primary": True, "verified": True},
        ]
    ) == "me@x.com"


def test_기본이_인증전이면_인증된_다른_주소를_쓴다():
    assert github.pick_email(
        [
            {"email": "unverified@x.com", "primary": True, "verified": False},
            {"email": "ok@x.com", "primary": False, "verified": True},
        ]
    ) == "ok@x.com"


def test_인증된_주소가_하나도_없으면_None():
    """**지어내지 않는다.** 없으면 계정을 안 만든다 (헌법 2-2)."""
    assert github.pick_email([{"email": "x@x.com", "primary": True, "verified": False}]) is None
    assert github.pick_email([]) is None


# ------------------------------------------------------------ 계정 잇기

def test_인증안된_이메일로는_남의_계정에_못_붙는다(app_module):
    """**이 파일에서 제일 중요한 테스트다.**

    GitHub 은 확인 안 된 주소도 계정에 달게 해 준다. 그걸 믿고 이으면
    아무나 남의 주소를 자기 GitHub 에 적어 두고 그 계정을 가져간다.
    """
    client = TestClient(app_module.app)
    client.post(
        "/api/v1/auth/signup",
        json={"email": "victim@x.com", "password": "qweasdzxc123"},
    )

    # pick_email 이 None 을 준 상황 — 인증된 주소가 없다
    with pytest.raises(Exception) as caught:
        app_module.accounts.link_or_create_github(9999, "attacker", None)
    assert getattr(caught.value, "code", "") == "NO_VERIFIED_EMAIL"

    # victim 계정은 그대로다 — github_id 가 안 붙었다
    import sqlite3

    conn = sqlite3.connect(app_module.DB_PATH)
    got = conn.execute(
        "SELECT github_id FROM users WHERE email = ?", ("victim@x.com",)
    ).fetchone()
    assert got[0] is None


def test_인증된_이메일이_같으면_기존_계정에_잇는다(app_module):
    client = TestClient(app_module.app)
    client.post(
        "/api/v1/auth/signup", json={"email": "me@x.com", "password": "qweasdzxc123"}
    )
    linked = app_module.accounts.link_or_create_github(4242, "me", "me@x.com")
    assert linked.email == "me@x.com"

    # **계정이 하나여야 한다.** 둘이 되면 검사 목록이 갈린다.
    assert app_module.accounts.count_users() == 1


def test_github_id_가_이메일보다_세다(app_module):
    """GitHub 에서 기본 이메일을 바꿔도 같은 계정으로 들어와야 한다."""
    first = app_module.accounts.link_or_create_github(777, "dev", "old@x.com")
    again = app_module.accounts.link_or_create_github(777, "dev-renamed", "brand-new@x.com")
    assert again.id == first.id
    assert again.email == "old@x.com"
    assert app_module.accounts.count_users() == 1


def test_처음_보는_사람은_계정이_생긴다(app_module):
    made = app_module.accounts.link_or_create_github(31337, "newbie", "new@x.com")
    assert made.email == "new@x.com"
    assert app_module.accounts.find_user(made.id) is not None


def test_github_전용_계정은_비밀번호로_못_연다(app_module):
    """표식이 scrypt 해시가 아니라서 어떤 값으로도 안 맞는다."""
    app_module.accounts.link_or_create_github(555, "gh", "gh@x.com")
    client = TestClient(app_module.app)
    for guess in ("github-only", "qweasdzxc123", ""):
        res = client.post("/api/v1/auth/login", json={"email": "gh@x.com", "password": guess})
        assert res.status_code == 401, guess


def test_잇고_나면_그_사람의_검사가_보인다(app_module):
    """계정을 이었다는 말이 참이 되려면 세션이 실제로 그 계정이어야 한다."""
    client = TestClient(app_module.app)
    client.post("/api/v1/auth/signup", json={"email": "me@x.com", "password": "qweasdzxc123"})
    before = client.get("/api/v1/auth/me").json()["user"]["email"]

    linked = app_module.accounts.link_or_create_github(4242, "me", "me@x.com")
    token, _ = app_module.accounts.open_session(linked.id)
    fresh = TestClient(app_module.app)
    fresh.cookies.set(app_module.SESSION_COOKIE, token)
    assert fresh.get("/api/v1/auth/me").json()["user"]["email"] == before


# ------------------------------------------------------------ 돌아갈 곳

@pytest.mark.parametrize(
    "raw",
    ["https://evil.example", "//evil.example", "/../admin", "javascript:alert(1)", None, ""],
)
def test_아무_데로나_못_보낸다(raw):
    """오픈 리다이렉트 — 우리 로그인 링크가 남의 사이트로 떨어뜨리는 미끼가 되면 안 된다."""
    assert github.safe_next(raw) == "/mine"


def test_아는_경로는_그대로_간다():
    assert github.safe_next("/check") == "/check"


# ------------------------------------------------------------ 엔드포인트

def test_승인_화면으로_보낸다(app_module):
    client = TestClient(app_module.app)
    res = client.get("/api/v1/auth/github/start", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"].startswith(github.AUTHORIZE_URL)
    assert "client_id=iv1.test" in res.headers["location"]


def test_저장소_권한은_요구하지_않는다(app_module):
    """로그인하려고 눌렀는데 "모든 저장소를 읽습니다" 가 뜨면 거기서 그만둔다."""
    client = TestClient(app_module.app)
    res = client.get("/api/v1/auth/github/start", follow_redirects=False)
    assert "repo" not in github.SCOPE
    assert "scope=read%3Auser+user%3Aemail" in res.headers["location"]


def test_취소하면_오류가_아니라_로그인_화면이다(app_module):
    client = TestClient(app_module.app)
    res = client.get(
        "/api/v1/auth/github/callback?error=access_denied", follow_redirects=False
    )
    assert res.status_code == 302
    assert res.headers["location"] == "http://web.test/login?error=cancelled"


def test_위조된_콜백은_세션을_안_준다(app_module):
    client = TestClient(app_module.app)
    res = client.get(
        "/api/v1/auth/github/callback?code=abc&state=forged", follow_redirects=False
    )
    assert res.status_code == 302
    assert "error=bad_state" in res.headers["location"]
    assert app_module.SESSION_COOKIE not in res.cookies


def test_설정이_없으면_기능이_없다(tmp_path, monkeypatch):
    """**있는 척하지 않는다.** 화면은 이 값을 보고 버튼을 아예 안 그린다."""
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "off.db"))
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)
    import importlib

    from web import app as app_module

    off = importlib.reload(app_module)
    client = TestClient(off.app)
    assert client.get("/api/v1/auth/me").json()["github"]["enabled"] is False
    assert client.get("/api/v1/auth/github/start", follow_redirects=False).status_code == 404


def test_켜져_있으면_화면에_알린다(app_module):
    client = TestClient(app_module.app)
    assert client.get("/api/v1/auth/me").json()["github"]["enabled"] is True
