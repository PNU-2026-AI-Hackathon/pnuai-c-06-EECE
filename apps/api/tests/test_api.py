"""HTTP 층 — FastAPI TestClient.

fastapi 가 없는 환경에서는 통째로 건너뛴다. 서비스 층 테스트는 그대로 돈다.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"
LOCAL_ORIGIN = "http://localhost:5173"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("ALLOWED_ORIGINS", LOCAL_ORIGIN)
    import importlib

    from web import app as app_module

    importlib.reload(app_module)
    return TestClient(app_module.app)


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_rules_includes_unimplemented(client):
    rules = client.get("/api/v1/rules").json()["rules"]
    assert len(rules) == 11
    assert any(r["implemented"] is False for r in rules)
    r12 = next(r for r in rules if r["id"] == "R12")
    assert r12["implemented"] is True
    assert r12["needs"] == ["netlist"]


def test_create_then_fetch(client):
    res = client.post(
        "/api/v1/checks",
        files={"netlist": (FIXTURE.name, FIXTURE.read_bytes(), "text/plain")},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "done"

    got = client.get(f"/api/v1/checks/{body['check_id']}")
    assert got.status_code == 200
    result = got.json()
    assert len(result["findings"]) == 3
    assert [f["rule"] for f in result["findings"]] == ["R12", "R12", "R11"]


def test_missing_netlist_returns_contract_error(client):
    res = client.post("/api/v1/checks", files={})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "NETLIST_REQUIRED"


def test_unknown_check_id_is_404(client):
    res = client.get("/api/v1/checks/chk_nope")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "CHECK_NOT_FOUND"


def test_cors_preflight_for_multipart_upload(client):
    """0-2. GET 만 열어두면 업로드가 통째로 막힌다."""
    res = client.options(
        "/api/v1/checks",
        headers={
            "Origin": LOCAL_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == LOCAL_ORIGIN
    assert "POST" in res.headers["access-control-allow-methods"]


def test_cors_header_on_actual_post(client):
    res = client.post(
        "/api/v1/checks",
        files={"netlist": (FIXTURE.name, FIXTURE.read_bytes(), "text/plain")},
        headers={"Origin": LOCAL_ORIGIN},
    )
    assert res.headers.get("access-control-allow-origin") == LOCAL_ORIGIN
