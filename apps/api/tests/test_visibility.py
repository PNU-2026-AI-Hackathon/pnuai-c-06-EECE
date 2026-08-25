"""비공개 링크.

**유료가 아니라 무료 기능이다.** 보안을 요금제 뒤에 두면 돈을 안 내는 사람의
회로도를 인질로 잡는 셈이 된다.

이 테스트가 지키는 것 —

1. 기본은 `link` 다 (지금까지 보낸 링크가 조용히 죽으면 안 된다)
2. 비공개면 **남은 404**, 주인은 열린다
3. 없는 검사와 남의 비공개 검사가 **구분되지 않는다**
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conftest import sign_in


def _make_check(client: TestClient, netlist_path) -> str:
    with open(netlist_path, "rb") as f:
        r = client.post("/api/v1/checks", files={"netlist": ("b.d356", f.read())})
    assert r.status_code == 201, r.text
    return r.json()["check_id"]


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
def client(app_module):
    return TestClient(app_module.app)


@pytest.fixture()
def other(app_module):
    """같은 서버를 보는 **다른 브라우저.** 쿠키를 공유하지 않는다."""
    return TestClient(app_module.app)


@pytest.fixture()
def netlist():
    import pathlib

    return pathlib.Path(__file__).parent / "fixtures/esp32-c6-presence-smart-light.d356"


def test_기본은_링크_공개다(signed_in, netlist):
    """지금까지 만든 검사가 전부 이렇게 동작했다. 기본을 바꾸면 링크가 죽는다."""
    cid = _make_check(signed_in, netlist)
    assert signed_in.get(f"/api/v1/checks/{cid}").json()["visibility"] == "link"


def test_공개_검사는_남도_연다(signed_in, netlist, other):
    cid = _make_check(signed_in, netlist)
    assert other.get(f"/api/v1/checks/{cid}").status_code == 200


def test_비공개로_바꾸면_남은_못_연다(signed_in, netlist, other):
    cid = _make_check(signed_in, netlist)
    signed_in.post(f"/api/v1/checks/{cid}/visibility", json={"visibility": "private"})

    assert other.get(f"/api/v1/checks/{cid}").status_code == 404
    assert signed_in.get(f"/api/v1/checks/{cid}").status_code == 200


def test_없는_검사와_남의_비공개_검사가_구분되지_않는다(signed_in, netlist, other):
    """**403 을 주면 「여기 뭔가 있다」를 알려주는 것이다.**

    ID 를 못 맞히는 것이 접근 통제의 전부라, 존재 자체를 안 알려야 한다.
    """
    cid = _make_check(signed_in, netlist)
    signed_in.post(f"/api/v1/checks/{cid}/visibility", json={"visibility": "private"})

    hidden = other.get(f"/api/v1/checks/{cid}")
    missing = other.get("/api/v1/checks/chk_" + "0" * 32)
    assert hidden.status_code == missing.status_code == 404
    assert hidden.json()["error"]["code"] == missing.json()["error"]["code"]


def test_다시_공개로_되돌릴_수_있다(signed_in, netlist, other):
    cid = _make_check(signed_in, netlist)
    signed_in.post(f"/api/v1/checks/{cid}/visibility", json={"visibility": "private"})
    signed_in.post(f"/api/v1/checks/{cid}/visibility", json={"visibility": "link"})
    assert other.get(f"/api/v1/checks/{cid}").status_code == 200


def test_주인이_아니면_바꿀_수_없다(signed_in, netlist, other):
    cid = _make_check(signed_in, netlist)
    sign_in(other, email="other@example.invalid")
    assert other.post(f"/api/v1/checks/{cid}/visibility", json={"visibility": "private"}).status_code == 404


def test_모르는_값은_거절한다(signed_in, netlist):
    cid = _make_check(signed_in, netlist)
    r = signed_in.post(f"/api/v1/checks/{cid}/visibility", json={"visibility": "public"})
    assert r.status_code == 400
