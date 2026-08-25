"""API 키.

**웹 화면 없이 검사를 돌리는 길이다.** 요금표의 Pro 가 파는 것이고
GitHub 연동도 이 키로 붙는다.

이 테스트가 지키는 것 —

1. **원문이 DB 에 안 남는다** (세션 토큰과 같은 규칙)
2. 키로 실제 검사가 된다
3. 지운 키는 즉시 안 먹는다
4. 남의 키를 못 건드린다
"""

from __future__ import annotations

import pathlib
import sqlite3

import pytest
from fastapi.testclient import TestClient

FIXTURE = pathlib.Path(__file__).parent / "fixtures/esp32-c6-presence-smart-light.d356"


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "500")
    monkeypatch.setenv("AUTH_LIMIT_PER_MINUTE", "500")
    import importlib

    from web import app as module

    importlib.reload(module)
    return module


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "api.db"


@pytest.fixture()
def client(app_module):
    return TestClient(app_module.app)


@pytest.fixture()
def other(app_module):
    return TestClient(app_module.app)


def _signup(c, email="key@example.invalid"):
    r = c.post("/api/v1/auth/signup", json={"email": email, "password": "correct horse battery staple"})
    assert r.status_code == 201, r.text


def _make_key(c, label="CI"):
    r = c.post("/api/v1/keys", json={"label": label})
    assert r.status_code == 201, r.text
    return r.json()["token"]


# ── 원문을 남기지 않는다 ────────────────────────────────────

def test_원문이_DB에_없다(client, app_module):
    """**DB 가 새도 그 파일만으로는 남의 계정에 못 들어간다.**"""
    _signup(client)
    token = _make_key(client)

    conn = sqlite3.connect(app_module.DB_PATH)
    rows = conn.execute("SELECT * FROM api_keys").fetchall()
    blob = " ".join(str(cell) for row in rows for cell in row)
    assert token not in blob
    assert len(rows) == 1


def test_목록에도_원문이_없다(client):
    _signup(client)
    token = _make_key(client)
    assert token not in client.get("/api/v1/keys").text


# ── 실제로 인증이 된다 ──────────────────────────────────────

def test_키로_검사를_만들_수_있다(other, client):
    """**쿠키 없이.** CI 러너에는 브라우저가 없다."""
    _signup(client)
    token = _make_key(client)

    r = other.post(
        "/api/v1/checks",
        headers={"Authorization": f"Bearer {token}"},
        files={"netlist": ("b.d356", FIXTURE.read_bytes())},
    )
    assert r.status_code == 201, r.text
    assert r.json()["owned"] is True


def test_키로_만든_검사가_내_검사에_뜬다(other, client):
    _signup(client)
    token = _make_key(client)
    other.post(
        "/api/v1/checks",
        headers={"Authorization": f"Bearer {token}"},
        files={"netlist": ("b.d356", FIXTURE.read_bytes())},
    )
    assert len(client.get("/api/v1/checks/mine").json()["checks"]) == 1


def test_지운_키는_안_먹는다(other, client):
    _signup(client)
    token = _make_key(client)
    key_id = client.get("/api/v1/keys").json()["keys"][0]["id"]
    client.delete(f"/api/v1/keys/{key_id}")

    r = other.post(
        "/api/v1/checks",
        headers={"Authorization": f"Bearer {token}"},
        files={"netlist": ("b.d356", FIXTURE.read_bytes())},
    )
    assert r.status_code == 401


def test_틀린_키는_로그인_안_된_것으로_본다(other):
    r = other.post(
        "/api/v1/checks",
        headers={"Authorization": "Bearer prefab_" + "0" * 64},
        files={"netlist": ("b.d356", FIXTURE.read_bytes())},
    )
    assert r.status_code == 401


# ── 남의 것을 못 건드린다 ───────────────────────────────────

def test_남의_키를_못_지운다(client, other):
    _signup(client)
    _make_key(client)
    key_id = client.get("/api/v1/keys").json()["keys"][0]["id"]

    _signup(other, email="stranger@example.invalid")
    assert other.delete(f"/api/v1/keys/{key_id}").status_code == 404
    assert len(client.get("/api/v1/keys").json()["keys"]) == 1


def test_남의_키가_목록에_안_보인다(client, other):
    _signup(client)
    _make_key(client)
    _signup(other, email="stranger@example.invalid")
    assert other.get("/api/v1/keys").json()["keys"] == []


# ── 한도와 입력 ────────────────────────────────────────────

def test_개수_상한이_있다(client):
    from web import apikeys

    _signup(client)
    for i in range(apikeys.MAX_KEYS_PER_USER):
        _make_key(client, f"키{i}")
    r = client.post("/api/v1/keys", json={"label": "하나 더"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "TOO_MANY_KEYS"


def test_이름이_없으면_거절한다(client):
    _signup(client)
    assert client.post("/api/v1/keys", json={"label": "  "}).status_code == 400


def test_키가_prefab으로_시작한다(client):
    """**저장소에 실수로 커밋됐을 때 알아볼 수 있어야 한다.**"""
    _signup(client)
    assert _make_key(client).startswith("prefab_")


def test_비로그인은_키를_못_만든다(other):
    assert other.post("/api/v1/keys", json={"label": "x"}).status_code == 401
