"""상태 배지 — **남의 README 에 붙는 우리 얼굴.**

지키는 것 넷 —

    1. 0건을 「통과」라고 말하지 않는다 (헌법 2-4)
    2. 못 찾은 검사를 초록으로 칠하지 않는다
    3. 없는 검사에도 깨진 이미지 대신 배지를 준다
    4. 로그인 없이 뜬다 — README 는 로그아웃한 사람이 본다
"""

from __future__ import annotations

import pathlib
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from web import badge

FIXTURE = pathlib.Path(__file__).parent / "fixtures/esp32-c6-presence-smart-light.d356"


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "500")
    monkeypatch.setenv("AUTH_LIMIT_PER_MINUTE", "500")
    import importlib

    from web import app as app_module

    return importlib.reload(app_module)


# ────────────────────────────────────────────── 문구

def test_치명이_있으면_치명을_말한다():
    text, color = badge.summarize(3, 1)
    assert "치명" in text and "3" in text
    assert color == badge.COLORS["crit"]


def test_치명이_없고_경고만_있으면_경고를_말한다():
    text, color = badge.summarize(0, 2)
    assert "경고" in text
    assert color == badge.COLORS["warn"]


def test_0건을_통과라고_말하지_않는다():
    """**못 돌린 규칙이 있을 수 있고 배지에는 그걸 적을 자리가 없다.**

    「통과」는 다 봤다는 뜻인데 우리는 그걸 보장 못 한다.
    """
    text, _ = badge.summarize(0, 0)
    assert "통과" not in text and "안전" not in text and "이상 없음" not in text
    assert text == "발견 없음"


def test_모르는_것을_초록으로_칠하지_않는다():
    _, color = badge.unknown()
    assert color != badge.COLORS["ok"]


# ────────────────────────────────────────────── SVG

@pytest.mark.parametrize("right", ["치명 3건", "발견 없음", "검사 없음", "경고 12건"])
def test_유효한_SVG_다(right):
    """깨진 SVG 는 README 에 깨진 이미지로 뜬다."""
    root = ET.fromstring(badge.render(right, "#D6293E"))
    assert root.tag.endswith("svg")
    assert int(root.get("width")) > 0


def test_긴_글자가_배지_밖으로_안_나간다():
    """SVG 에는 줄바꿈이 없다. 폭을 안 재면 글자가 삐져나온다."""
    narrow = int(ET.fromstring(badge.render("발견 없음", "#000")).get("width"))
    wide = int(ET.fromstring(badge.render("치명 1234건", "#000")).get("width"))
    assert wide > narrow


def test_읽어주는_이름이_붙는다():
    """색만으로 상태를 말하지 않는다 (헌법 8절)."""
    root = ET.fromstring(badge.render("치명 3건", "#000"))
    assert "치명 3건" in root.get("aria-label")


# ────────────────────────────────────────────── 엔드포인트

def _make(client) -> str:
    client.post("/api/v1/auth/signup", json={"email": "b@b.com", "password": "qweasdzxc123"})
    res = client.post("/api/v1/checks", files={"netlist": ("b.d356", FIXTURE.read_bytes())})
    return res.json()["check_id"]


def test_로그인_없이_뜬다(app_module):
    """README 는 로그아웃한 사람이 본다. 배지가 안 뜨면 그 저장소가 깨져 보인다."""
    owner = TestClient(app_module.app)
    cid = _make(owner)

    stranger = TestClient(app_module.app)
    res = stranger.get(f"/api/v1/checks/{cid}/badge.svg")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/svg+xml")


def test_없는_검사에도_깨진_이미지_대신_배지를_준다(app_module):
    client = TestClient(app_module.app)
    res = client.get("/api/v1/checks/chk_없는것/badge.svg")
    assert res.status_code == 200
    assert "검사 없음" in res.text


def test_비공개로_바꿔도_배지는_뜬다(app_module):
    """배지에는 회로도도 코드도 안 실린다. **내용은 안 주고 상태만 준다.**"""
    owner = TestClient(app_module.app)
    cid = _make(owner)
    owner.post(f"/api/v1/checks/{cid}/visibility", json={"visibility": "private"})

    stranger = TestClient(app_module.app)
    # 결과 본문은 못 본다
    assert stranger.get(f"/api/v1/checks/{cid}").status_code == 404
    # 그래도 배지는 뜬다
    assert stranger.get(f"/api/v1/checks/{cid}/badge.svg").status_code == 200


def test_캐시가_짧다(app_module):
    """길면 고쳐진 뒤에도 빨간 배지가 며칠 남는다."""
    client = TestClient(app_module.app)
    cid = _make(client)
    cache = client.get(f"/api/v1/checks/{cid}/badge.svg").headers.get("cache-control", "")
    assert "max-age" in cache
    seconds = int(cache.split("max-age=")[1].split(",")[0])
    assert seconds <= 300
