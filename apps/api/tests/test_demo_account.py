"""공용 구경 계정.

**README 가 이 계정을 적어 두고 있다.** 그런데 무료 플랜이라 재배포마다 DB 가
비워져서, 8/26 에 실제로 로그인해 보니 401 이었다 — **문서에 적힌 것이 거짓이었다.**

문서가 지킬 수 없는 약속이면 코드가 지켜야 한다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("AUTH_LIMIT_PER_MINUTE", "500")
    import importlib

    from web import app as app_module

    return importlib.reload(app_module)


def test_빈_DB_에서도_계정이_있다(app_module):
    """재배포 직후 상태다. 여기서 안 되면 심사위원이 못 들어온다."""
    client = TestClient(app_module.app)
    res = client.post(
        "/api/v1/auth/login",
        json={"email": app_module.DEMO_EMAIL, "password": app_module.DEMO_PASSWORD},
    )
    assert res.status_code == 200, res.text


def test_두_번_떠도_안_깨진다(app_module, tmp_path, monkeypatch):
    """기동 때마다 심는데, 이미 있으면 EMAIL_TAKEN 으로 죽으면 안 된다."""
    import importlib

    from web import app as mod

    again = importlib.reload(mod)
    assert again.DEMO_ACCOUNT_READY is True
    client = TestClient(again.app)
    assert client.post(
        "/api/v1/auth/login",
        json={"email": again.DEMO_EMAIL, "password": again.DEMO_PASSWORD},
    ).status_code == 200


def test_되는지를_루트에서_말한다(app_module):
    """**심었다고 말하지 않고 실제로 되는지 말한다.** 여기가 거짓이면 README 도 거짓이다."""
    client = TestClient(app_module.app)
    assert client.get("/").json()["demo_account"] == app_module.DEMO_EMAIL


def test_공용_계정으로_검사가_된다(app_module):
    """로그인만 되고 검사가 안 되면 심사위원은 같은 자리에서 막힌다."""
    import pathlib

    board = pathlib.Path(__file__).parent / "fixtures/esp32-c6-presence-smart-light.d356"
    client = TestClient(app_module.app)
    client.post(
        "/api/v1/auth/login",
        json={"email": app_module.DEMO_EMAIL, "password": app_module.DEMO_PASSWORD},
    )
    res = client.post("/api/v1/checks", files={"netlist": ("b.d356", board.read_bytes())})
    assert res.status_code == 201
    assert res.json()["owned"] is True
