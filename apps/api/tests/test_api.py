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
    # **쿠키가 `Secure` 면 TestClient(http)가 버린다.** 그러면 로그인이 조용히
    # 안 되고, 검사가 401 로 막힌다 — 로그인 벽이 생기면서 실제로 그랬다.
    monkeypatch.setenv("COOKIE_SECURE", "0")
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
    # **개수를 손으로 못 박지 않는다.** 규칙이 늘 때마다 세 곳을 고치게 된다 (헌법 7절).
    from prefab import catalog

    assert len(rules) == catalog.TOTAL
    assert all(isinstance(r["implemented"], bool) for r in rules)
    r12 = next(r for r in rules if r["id"] == "R12")
    assert r12["implemented"] is True
    assert r12["needs"] == ["netlist"]


def test_create_then_fetch(signed_in):
    res = signed_in.post(
        "/api/v1/checks",
        files={"netlist": (FIXTURE.name, FIXTURE.read_bytes(), "text/plain")},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "done"

    got = signed_in.get(f"/api/v1/checks/{body['check_id']}")
    assert got.status_code == 200
    result = got.json()
    assert len(result["findings"]) == 2
    assert [f["rule"] for f in result["findings"]] == ["R12", "R12"]


def test_missing_netlist_returns_contract_error(signed_in):
    res = signed_in.post("/api/v1/checks", files={})
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


def test_회로도_넷리스트도_업로드된다(signed_in):
    """계약 확장 — `netlist` 슬롯이 kicadxml 도 받는다.

    형식은 확장자가 아니라 **내용으로** 가른다. 사용자는 파일 이름을 바꾼다.
    """
    res = signed_in.post(
        "/api/v1/checks",
        files={"netlist": (XML_FIXTURE.name, XML_FIXTURE.read_bytes(), "text/xml")},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "done"

    result = signed_in.get(f"/api/v1/checks/{body['check_id']}").json()
    assert result["inputs"]["netlist"]["nets"] > 0
    # 회로도 넷리스트라는 것을 파이프라인이 그대로 말한다 (헌법 2-4)
    parse_step = result["pipeline"][0]
    assert "좌표 없음" in parse_step["detail"]


def test_확장자가_txt_여도_내용으로_가른다(signed_in):
    """계약이 `.txt` 를 허용한다. 그 안에 무엇이 들었는지는 내용만 안다."""
    res = signed_in.post(
        "/api/v1/checks",
        files={"netlist": ("board.txt", XML_FIXTURE.read_bytes(), "text/plain")},
    )
    assert res.status_code == 201
    result = signed_in.get(f"/api/v1/checks/{res.json()['check_id']}").json()
    assert "좌표 없음" in result["pipeline"][0]["detail"]


def test_받지_않는_확장자는_그대로_거절한다(signed_in):
    res = signed_in.post(
        "/api/v1/checks",
        files={"netlist": ("board.kicad_sch", b"(kicad_sch)", "text/plain")},
    )
    assert res.status_code == 415


def test_기동_때_커밋된_부품_사실을_심는다(client):
    """배포 이미지에는 DB 가 없다. 안 심으면 데이터시트 해제가 조용히 사라진다.

    `prefab.db` 는 `.gitignore` 라서 커밋되는 진실은 `parts/*.json` 뿐이다.
    그것으로 기동 때 다시 만들기 때문에 **영구 디스크가 필요 없다.**
    """
    seeded = client.get("/").json()["seeded_parts"]
    assert seeded, "부품 사실이 하나도 안 심겼다 — 해제 경로가 죽는다"
    assert "HLK-LD2410C" in seeded


def test_서식_파일은_사실로_안_센다(client):
    """`_TEMPLATE.json` 은 사람이 채우라고 둔 서식이지 부품이 아니다."""
    assert all(not s.startswith("_") for s in client.get("/").json()["seeded_parts"])


def test_사실_폴더가_없어도_서버는_뜬다(tmp_path, monkeypatch):
    """사실 하나 때문에 서버가 안 뜨면 그게 훨씬 나쁘다."""
    from web import service
    store = service.Store(tmp_path / "t.db")
    assert service.seed_facts(tmp_path / "없는폴더", store) == []


# ── CORS — 배포 주소를 넣어도 개발이 안 막혀야 한다 ──────────────────
#
# 실제로 밟았다. Render 에 `ALLOWED_ORIGINS=https://prefab-web.onrender.com` 을
# 넣는 순간 로컬 개발이 통째로 막혔다. 증상이 고약하다 — **화면은 멀쩡히 뜨고
# 검사만 조용히 실패한다.** 배포한 사람은 자기가 무엇을 껐는지 모른다.


@pytest.fixture()
def deployed_client(tmp_path, monkeypatch):
    """배포 상태를 그대로 흉내낸다 — 환경변수에 배포 주소만 들어 있다."""
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "deployed.db"))
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://prefab-web.onrender.com")
    import importlib

    from web import app as app_module

    importlib.reload(app_module)
    return TestClient(app_module.app)


def _preflight(client, origin: str):
    return client.options(
        "/api/v1/checks",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_배포_주소를_넣어도_개발_포트가_살아_있다(deployed_client):
    """`ALLOWED_ORIGINS` 는 **더하는 것**이지 대체하는 것이 아니다."""
    for port in (5173, 5174, 5175):
        for host in ("localhost", "127.0.0.1"):
            origin = f"http://{host}:{port}"
            res = _preflight(deployed_client, origin)
            assert res.headers.get("access-control-allow-origin") == origin, origin


def test_배포_주소가_허용된다(deployed_client):
    origin = "https://prefab-web.onrender.com"
    assert _preflight(deployed_client, origin).headers.get("access-control-allow-origin") == origin


def test_환경변수가_없어도_개발_포트는_열려_있다(tmp_path, monkeypatch):
    """아무것도 안 넣은 상태가 곧 로컬 개발 상태다."""
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "bare.db"))
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    import importlib

    from web import app as app_module

    importlib.reload(app_module)
    client = TestClient(app_module.app)
    assert _preflight(client, LOCAL_ORIGIN).headers.get("access-control-allow-origin") == LOCAL_ORIGIN


def test_아무_주소나_열리지는_않는다(deployed_client):
    """개발 포트를 더 연다고 문이 통째로 열리면 안 된다."""
    res = _preflight(deployed_client, "https://evil.example.com")
    assert res.headers.get("access-control-allow-origin") is None


# ── 이전 회로도 (드리프트) ──────────────────────────────────────────
#
# R10 은 이 제품의 이름이 붙은 규칙인데, 이전 회로도가 없으면 아무 말도 못 한다.
# 그런데 그 입력이 `NEEDS` 에 없어서 엔진은 R10 을 **실행함**으로 센다.
# 못 한 일을 실행했다고 적는 것이라, 리포트가 그 사실을 말하는지까지 본다 (헌법 2-4).

MOVED = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.moved-to-d4.d356"
FIRMWARE_DIR = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.firmware"


def _firmware_zip() -> bytes:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for f in sorted(FIRMWARE_DIR.iterdir()):
            if f.is_file():
                z.writestr(f.name, f.read_text(encoding="utf-8"))
    return buf.getvalue()


def _upload(client, *, previous: bytes | None = None):
    files = {
        "netlist": ("now.d356", MOVED.read_bytes(), "text/plain"),
        "firmware": ("fw.zip", _firmware_zip(), "application/zip"),
    }
    if previous is not None:
        files["previous_netlist"] = ("before.d356", previous, "text/plain")
    created = client.post("/api/v1/checks", files=files)
    assert created.status_code == 201, created.text
    return client.get(f"/api/v1/checks/{created.json()['check_id']}").json()


def _engine_step(result) -> str:
    return next(p["detail"] for p in result["pipeline"] if "규칙" in p["name"])


def test_이전_회로도를_주면_드리프트가_잡힌다(signed_in):
    r = _upload(signed_in, previous=FIXTURE.read_bytes())
    r10 = [f for f in r["findings"] if f["rule"] == "R10"]
    assert r10, [f["rule"] for f in r["findings"]]
    # 어디서 어디로 옮겼는지 문구에 그대로 있어야 사용자가 고칠 자리를 안다
    assert "D2" in r10[0]["claim"] and "D4" in r10[0]["claim"], r10[0]["claim"]


def test_이전_회로도가_없으면_R10_이_조용하다(signed_in):
    r = _upload(signed_in)
    assert not [f for f in r["findings"] if f["rule"] == "R10"]


def test_이전_회로도가_없으면_리포트가_그_사실을_말한다(signed_in):
    """**"12개 중 12개 실행" 만 적으면 R10 이 볼 것도 없이 돈 것을 숨기는 것이다.**"""
    r = _upload(signed_in)
    assert "이전 회로도가 없어" in _engine_step(r), _engine_step(r)


def test_이전_회로도를_주면_그_문구가_사라진다(signed_in):
    r = _upload(signed_in, previous=FIXTURE.read_bytes())
    assert "이전 회로도가 없어" not in _engine_step(r)


def test_깨진_이전_회로도는_조용히_버리지_않는다(signed_in):
    """조용히 버리면 사용자가 "드리프트 없음" 으로 읽는다. 실제로는 비교를 안 한 것이다."""
    res = signed_in.post(
        "/api/v1/checks",
        files={
            "netlist": ("now.d356", MOVED.read_bytes(), "text/plain"),
            "previous_netlist": ("before.xml", b"<not-a-netlist/>", "text/xml"),
        },
    )
    assert res.status_code == 422, res.text
    body = res.json()["error"]
    assert body["code"] == "PREVIOUS_NETLIST_PARSE_FAILED", body
    # 어느 파일을 고쳐야 하는지 말해 준다 — 둘 다 넷리스트라 구분이 없으면 못 찾는다
    assert "before.xml" in body["message"], body["message"]


def test_이전_회로도_없이도_검사는_그대로_된다(signed_in):
    """선택 입력이다. 안 줬다고 실패하면 안 된다."""
    r = _upload(signed_in)
    assert r["status"] == "done"
    assert r["summary"]["rules_run"] > 0


# ─────────────────────────────────────────── 출시 알림 대기 명단


def test_대기_명단은_이메일_하나만_받는다(client):
    """받는 것을 늘리지 않는다 — 이름·소속·전화번호는 물어볼 이유가 없다."""
    res = client.post("/api/v1/waitlist", json={"email": "me@example.com", "plan": "pro"})
    assert res.status_code == 201
    assert res.json() == {"joined": True}


def test_대기_명단은_인원_수를_안_돌려준다(client):
    """「3명 대기 중」 같은 숫자가 화면에 뜨면 오히려 안 팔리는 제품처럼 보인다."""
    body = client.post(
        "/api/v1/waitlist", json={"email": "a@example.com", "plan": "team"}
    ).json()
    assert "count" not in body and "total" not in body


def test_대기_명단_중복은_그대로_성공이다(client):
    """이미 등록했다고 알려 주면, 그 주소가 명단에 있다는 사실을 아무에게나 말하는 셈이다."""
    for _ in range(2):
        res = client.post("/api/v1/waitlist", json={"email": "me@example.com", "plan": "pro"})
        assert res.status_code == 201


def test_대기_명단_거절은_사유_코드를_그대로_준다(client):
    res = client.post("/api/v1/waitlist", json={"email": "아님", "plan": "pro"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "EMAIL_INVALID"

    res = client.post("/api/v1/waitlist", json={"email": "a@b.co", "plan": "gold"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "PLAN_UNKNOWN"


def test_대기_명단_본문이_객체가_아니면_거절한다(client):
    res = client.post("/api/v1/waitlist", json="문자열")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "BAD_REQUEST"
