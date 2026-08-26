"""재배포를 견디는 CI 키.

**8/26 하루에 세 번 죽었다.** 머지할 때마다 재배포가 나고, 무료 플랜이라 DB 가
통째로 비워지고, 키도 같이 사라진다. 그때마다 사람이 새 키를 만들어 시크릿에
넣었다 — 그리고 그 사이 CI 는 401 로 서 있었다.

배포 설정에 원문을 두면 기동 때마다 지문을 다시 심는다.
"""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from web import apikeys

CI = "prefab_" + "a" * 64


@pytest.fixture()
def app_with_key(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("AUTH_LIMIT_PER_MINUTE", "500")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "500")
    monkeypatch.setenv("PREFAB_CI_KEY", CI)
    import importlib

    from web import app as app_module

    return importlib.reload(app_module)


def test_빈_DB_에서도_CI_키가_바로_먹는다(app_with_key):
    """**재배포 직후 상태다.** 여기서 안 되면 CI 가 401 로 선다."""
    import pathlib

    board = pathlib.Path(__file__).parent / "fixtures/esp32-c6-presence-smart-light.d356"
    client = TestClient(app_with_key.app)
    res = client.post(
        "/api/v1/checks",
        files={"netlist": ("b.d356", board.read_bytes())},
        headers={"Authorization": f"Bearer {CI}"},
    )
    assert res.status_code == 201, res.text
    # **주인이 붙는다** — 게스트로 통과한 게 아니다
    assert res.json()["owned"] is True


def test_되는지를_루트에서_말한다(app_with_key):
    assert TestClient(app_with_key.app).get("/").json()["ci_key"] == "ready"


def test_안_넣었으면_안_넣었다고_말한다(tmp_path, monkeypatch):
    """**「ready」와 「unset」을 구분한다.** 뭉치면 왜 401 인지 못 찾는다."""
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "b.db"))
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.delenv("PREFAB_CI_KEY", raising=False)
    import importlib

    from web import app as app_module

    off = importlib.reload(app_module)
    assert TestClient(off.app).get("/").json()["ci_key"] == "unset"


def test_두_번_떠도_키가_하나다(app_with_key):
    """기동 때마다 심는데 쌓이면 안 된다."""
    import importlib

    from web import app as mod

    again = importlib.reload(mod)
    conn = sqlite3.connect(again.DB_PATH)
    n = conn.execute(
        "SELECT COUNT(*) FROM api_keys WHERE fingerprint = ?", (apikeys.fingerprint(CI),)
    ).fetchone()[0]
    assert n == 1


def test_원문을_저장하지_않는다(app_with_key):
    """**지문만 남는다.** DB 가 새도 그 파일로는 우리 API 를 못 부른다."""
    conn = sqlite3.connect(app_with_key.DB_PATH)
    for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        for row in conn.execute(f"SELECT * FROM {table}"):
            for cell in row:
                assert CI not in str(cell), f"{table} 에 키 원문이 들어갔습니다"


def test_모양이_아닌_값은_안_심는다():
    """오타나 빈 값을 심으면 못 쓰는 줄이 DB 에 남는다."""
    conn = sqlite3.connect(":memory:")
    apikeys.init(conn)
    for bad in ["", "그냥문자열", "sk-openai-something"]:
        assert apikeys.ensure(conn, "usr_1", bad, "x") is False
    assert conn.execute("SELECT COUNT(*) FROM api_keys").fetchone()[0] == 0
