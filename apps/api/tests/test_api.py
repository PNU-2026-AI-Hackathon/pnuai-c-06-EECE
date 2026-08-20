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


def test_rules_exposes_every_rule_with_its_state(client):
    """구현 여부를 규칙마다 실어 보낸다. 미구현도 숨기지 않는다.

    원래 "미구현이 하나는 있다"를 단정했는데 11/11 이 되면서 깨졌다.
    지키려던 것은 개수가 아니라 노출이다.
    """
    rules = client.get("/api/v1/rules").json()["rules"]
    assert len(rules) == 12
    assert all(isinstance(r["implemented"], bool) for r in rules)
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
    assert len(result["findings"]) == 2
    assert [f["rule"] for f in result["findings"]] == ["R12", "R12"]


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


XML_FIXTURE = Path(__file__).parent / "fixtures" / "schematic-gpio-named.net.xml"


def test_회로도_넷리스트도_업로드된다(client):
    """계약 확장 — `netlist` 슬롯이 kicadxml 도 받는다.

    형식은 확장자가 아니라 **내용으로** 가른다. 사용자는 파일 이름을 바꾼다.
    """
    res = client.post(
        "/api/v1/checks",
        files={"netlist": (XML_FIXTURE.name, XML_FIXTURE.read_bytes(), "text/xml")},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "done"

    result = client.get(f"/api/v1/checks/{body['check_id']}").json()
    assert result["inputs"]["netlist"]["nets"] > 0
    # 회로도 넷리스트라는 것을 파이프라인이 그대로 말한다 (헌법 2-4)
    parse_step = result["pipeline"][0]
    assert "좌표 없음" in parse_step["detail"]


def test_확장자가_txt_여도_내용으로_가른다(client):
    """계약이 `.txt` 를 허용한다. 그 안에 무엇이 들었는지는 내용만 안다."""
    res = client.post(
        "/api/v1/checks",
        files={"netlist": ("board.txt", XML_FIXTURE.read_bytes(), "text/plain")},
    )
    assert res.status_code == 201
    result = client.get(f"/api/v1/checks/{res.json()['check_id']}").json()
    assert "좌표 없음" in result["pipeline"][0]["detail"]


def test_받지_않는_확장자는_그대로_거절한다(client):
    res = client.post(
        "/api/v1/checks",
        files={"netlist": ("board.kicad_sch", b"(kicad_sch)", "text/plain")},
    )
    assert res.status_code == 415
