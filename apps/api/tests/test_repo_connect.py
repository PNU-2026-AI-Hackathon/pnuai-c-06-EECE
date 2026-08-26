"""저장소 연동 엔드포인트.

**이 파일이 지키는 것은 토큰이다.**

    1. 접근 토큰을 DB 에 안 넣는다        ← 제일 중요하다
    2. 일이 끝나면 토큰을 버린다
    3. 로그인 안 한 사람은 못 부른다
    4. 저장소 권한은 **연동을 누를 때** 물어본다 (로그인 때가 아니다)
    5. 저장소가 잘려서 다 못 봤으면 그렇게 말한다
"""

from __future__ import annotations

import sqlite3

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


@pytest.fixture()
def signed_in(app_module):
    client = TestClient(app_module.app)
    client.post("/api/v1/auth/signup", json={"email": "me@x.com", "password": "qweasdzxc123"})
    return client


# ------------------------------------------------------------ 권한 나누기

def test_로그인_권한과_저장소_권한이_다르다():
    """로그인하려고 눌렀는데 "모든 저장소를 읽고 씁니다" 가 뜨면 거기서 그만둔다."""
    assert "repo" not in github.SCOPE
    assert "repo" in github.CONNECT_SCOPE
    assert "workflow" in github.CONNECT_SCOPE


def test_저장소_권한은_연동을_누를_때_물어본다(signed_in):
    res = signed_in.get("/api/v1/github/connect/start", follow_redirects=False)
    assert res.status_code == 302
    assert "scope=repo+workflow" in res.headers["location"]


def test_로그인_안_한_사람은_연동을_못_시작한다(app_module):
    client = TestClient(app_module.app)
    assert client.get("/api/v1/github/connect/start", follow_redirects=False).status_code == 401


# ------------------------------------------------------------ 토큰

def test_접근_토큰이_DB_에_안_남는다(signed_in, app_module):
    """**이 파일에서 제일 중요한 테스트다.**

    저장하면 우리 DB 가 남의 비공개 회로도 저장소 열쇠를 들고 있게 된다.
    지금 우리에게는 그걸 지킬 암호화도, 살아남는 저장소도 없다.
    """
    fake = "gho_" + "f" * 36
    signed_in.cookies.set(app_module.CONNECT_COOKIE, fake)

    conn = sqlite3.connect(app_module.DB_PATH)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for table in tables:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        for row in rows:
            for cell in row:
                assert fake not in str(cell), f"{table} 에 접근 토큰이 들어갔습니다"


def test_토큰이_없으면_401_이고_다시_연결하라고_한다(signed_in):
    res = signed_in.get("/api/v1/github/repos")
    assert res.status_code == 401
    assert "다시 연결" in res.json()["error"]["message"]


def test_일이_끝나면_토큰을_버린다(signed_in, app_module, monkeypatch):
    """PR 을 열고 나면 더 들고 있을 이유가 없다."""
    monkeypatch.setattr(github, "open_setup_pr", lambda *a, **k: "https://github.com/x/y/pull/1")
    signed_in.cookies.set(app_module.CONNECT_COOKIE, "gho_whatever")

    res = signed_in.post(
        "/api/v1/github/setup",
        json={"repo": "x/y", "branch": "main", "netlist": "hw/board.d356"},
    )
    assert res.status_code == 200
    assert res.json()["pull_request"].endswith("/pull/1")
    # 응답이 쿠키를 지우라고 말하는가
    assert 'prefab_gh_connect=""' in res.headers.get("set-cookie", "") or \
           "Max-Age=0" in res.headers.get("set-cookie", "")


# ------------------------------------------------------------ 훑기

def test_다_못_봤으면_그렇게_말한다(signed_in, app_module, monkeypatch):
    """조용히 자르면 "넷리스트가 없습니다" 가 거짓이 된다 (헌법 2-2)."""
    monkeypatch.setattr(github, "list_paths", lambda *a, **k: (["README.md"], True))
    signed_in.cookies.set(app_module.CONNECT_COOKIE, "gho_whatever")

    got = signed_in.get("/api/v1/github/scan?repo=x/y&branch=main").json()
    assert got["truncated"] is True
    assert got["netlist"]["picked"] is None


def test_찾은_것을_근거와_함께_돌려준다(signed_in, app_module, monkeypatch):
    monkeypatch.setattr(
        github, "list_paths",
        lambda *a, **k: (["hardware/board.net.xml", "firmware/main/main.ino", "hardware/bom.csv"], False),
    )
    signed_in.cookies.set(app_module.CONNECT_COOKIE, "gho_whatever")

    got = signed_in.get("/api/v1/github/scan?repo=x/y&branch=main").json()
    assert got["netlist"]["picked"] == "hardware/board.net.xml"
    assert got["firmware"]["picked"] == "firmware/main"
    assert got["bom"]["picked"] == "hardware/bom.csv"
    assert all(c["reason"] for c in got["netlist"]["candidates"])


def test_넷리스트_없이는_PR_을_안_연다(signed_in, app_module):
    signed_in.cookies.set(app_module.CONNECT_COOKIE, "gho_whatever")
    res = signed_in.post("/api/v1/github/setup", json={"repo": "x/y", "branch": "main"})
    assert res.status_code == 422


def test_쓸_수_있는_저장소만_보여준다(signed_in, app_module, monkeypatch):
    """읽기만 되는 저장소를 골라 놓고 마지막에 막히면 헛수고다."""
    monkeypatch.setattr(
        github, "_get_json",
        lambda *a, **k: [
            {"full_name": "me/mine", "private": True, "default_branch": "main",
             "permissions": {"push": True}},
            {"full_name": "other/readonly", "private": False, "default_branch": "main",
             "permissions": {"push": False}},
        ],
    )
    signed_in.cookies.set(app_module.CONNECT_COOKIE, "gho_whatever")
    got = signed_in.get("/api/v1/github/repos").json()["repos"]
    assert [r["full_name"] for r in got] == ["me/mine"]


# ------------------------------------------------------------ 되돌릴 수 있게

def test_기본_브랜치에_직접_안_쓴다():
    """곧바로 커밋하면 마음에 안 들어도 이미 들어간 뒤다. PR 이면 닫으면 그만이다."""
    assert github.SETUP_BRANCH not in ("main", "master")


def test_PR_설명이_시크릿을_직접_넣으라고_말한다():
    """**우리가 대신 안 넣는다.** 그 권한을 받으면 저장소의 모든 비밀값을 바꿀 수 있다."""
    body = github._PR_BODY.format(path="x")
    assert "PREFAB_API_KEY" in body
    assert "대신 넣지 않습니다" in body
