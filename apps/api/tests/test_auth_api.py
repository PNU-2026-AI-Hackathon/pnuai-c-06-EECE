"""인증 HTTP 층 — 그리고 **로그인이 무엇을 막으면 안 되는지.**

헌법 4절 단서 1: *로그인은 더하는 것이지 막는 것이 아니다.* 이 파일의 절반은
그 약속을 지키는 테스트다. 로그인 벽이 생기면 "링크 하나로 근거까지 보인다"는
우리 최대 강점이 사라진다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

BOARD = Path(__file__).parent.parent / "board" / "board.net.xml"
GOOD = "correct horse battery staple"
LOCAL_ORIGIN = "http://localhost:5173"


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("ALLOWED_ORIGINS", LOCAL_ORIGIN)
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


def _signup(client, email="kim@example.com"):
    return client.post("/api/v1/auth/signup", json={"email": email, "password": GOOD})


def _check(client):
    return client.post(
        "/api/v1/checks", files={"netlist": ("b.net.xml", BOARD.read_bytes())}
    )


# ── 로그인이 막으면 안 되는 것 (헌법 4절 단서 1) ───────────────────

def test_로그인_없이도_검사가_된다(client):
    assert _check(client).status_code == 201


def test_로그인_없이_만든_결과는_누구나_연다(client, other):
    """**주소를 아는 사람이 여는 것**이 이 서비스의 공유 방식이다."""
    made = _check(client).json()
    assert made["owned"] is False
    assert other.get(f"/api/v1/checks/{made['check_id']}").status_code == 200


def test_예시_결과는_로그인_없이_열린다(client, app_module):
    sample = app_module.SAMPLE_CHECK_ID
    assert sample, "예시가 없으면 이 테스트는 아무것도 안 지킨다"
    assert client.get(f"/api/v1/checks/{sample}").status_code == 200


def test_me_는_로그아웃_상태를_오류로_만들지_않는다(client):
    """화면이 뜨자마자 부르는 자리다. 401 로 만들면 **콘솔이 401 로 가득 차고
    진짜 오류가 그 사이에 묻힌다.**"""
    body = client.get("/api/v1/auth/me").json()
    assert body["user"] is None


def test_규칙_카탈로그와_사용량은_로그인과_무관하다(client):
    assert client.get("/api/v1/rules").status_code == 200
    assert client.get("/api/v1/usage").status_code == 200


# ── 가입·로그인 ────────────────────────────────────────────────────

def test_가입하면_201_과_세션이_같이_온다(client):
    r = _signup(client)
    assert r.status_code == 201
    assert r.json()["email"] == "kim@example.com"
    assert client.get("/api/v1/auth/me").json()["user"]["email"] == "kim@example.com"


def test_응답에_비밀번호도_토큰도_없다(client):
    r = _signup(client)
    body = r.text
    assert GOOD not in body
    assert "password" not in body
    assert "token" not in body


def test_세션_쿠키는_스크립트가_못_읽는다(client):
    """`localStorage` 에 두면 **XSS 한 번이 곧 계정 탈취**가 된다."""
    r = _signup(client)
    raw = r.headers["set-cookie"]
    assert "httponly" in raw.lower()


def test_로그인과_로그아웃(client):
    _signup(client)
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").json()["user"] is None
    r = client.post("/api/v1/auth/login", json={"email": "kim@example.com", "password": GOOD})
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me").json()["user"] is not None


def test_틀린_비밀번호는_401(client):
    _signup(client)
    r = client.post("/api/v1/auth/login", json={"email": "kim@example.com", "password": "x" * 12})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "BAD_CREDENTIALS"


def test_이미_쓰는_이메일은_409(client, other):
    _signup(client)
    assert _signup(other).status_code == 409


def test_몸통이_비어도_500_이_아니다(client):
    """빈 요청에 500 이 나면 그 500 이 곧 "여기 뭔가 있다"는 신호가 된다."""
    r = client.post("/api/v1/auth/login", json={})
    assert r.status_code == 401


# ── 소유권 ──────────────────────────────────────────────────────────

def test_로그인하고_만든_검사에는_주인이_붙는다(client):
    _signup(client)
    assert _check(client).json()["owned"] is True


def test_남의_검사는_403_이_아니라_404_다(client, other):
    """403 은 **"그 ID 는 존재한다"** 를 알려 준다. 그것만으로 목록을 만들 수 있다."""
    _signup(client)
    mine = _check(client).json()["check_id"]
    r = other.get(f"/api/v1/checks/{mine}")
    assert r.status_code == 404


def test_로그아웃하면_내_검사도_안_보인다(client):
    _signup(client)
    mine = _check(client).json()["check_id"]
    client.post("/api/v1/auth/logout")
    assert client.get(f"/api/v1/checks/{mine}").status_code == 404


def test_내_검사_목록은_내_것만_담는다(client, other):
    _signup(client)
    _signup(other, email="lee@example.com")
    mine = _check(client).json()["check_id"]
    theirs = _check(other).json()["check_id"]

    ids = [c["check_id"] for c in client.get("/api/v1/checks/mine").json()["checks"]]
    assert ids == [mine]
    assert theirs not in ids


def test_목록_경로가_검사_ID_로_먹히지_않는다(client):
    """`/checks/mine` 이 `/checks/{id}` 보다 **먼저** 등록돼야 한다.

    순서가 바뀌면 `mine` 이 검사 ID 로 해석돼 404 가 되고, 목록이 조용히
    빈 화면이 된다.
    """
    _signup(client)
    assert client.get("/api/v1/checks/mine").status_code == 200


def test_목록에_본문을_통째로_싣지_않는다(client):
    """검사 50건의 전체 결과를 한 번에 내려보내면 수 MB 가 된다."""
    _signup(client)
    _check(client)
    row = client.get("/api/v1/checks/mine").json()["checks"][0]
    assert set(row) == {"check_id", "created_at", "summary", "netlist_filename"}
    assert row["netlist_filename"] == "b.net.xml"


def test_로그인_안_하면_목록을_못_본다(client):
    assert client.get("/api/v1/checks/mine").status_code == 401


# ── 삭제 ────────────────────────────────────────────────────────────

def test_내_검사를_내릴_수_있다(client):
    """로그인 전에는 **올린 결과를 내릴 방법이 아예 없었다.**"""
    _signup(client)
    mine = _check(client).json()["check_id"]
    assert client.delete(f"/api/v1/checks/{mine}").status_code == 200
    assert client.get(f"/api/v1/checks/{mine}").status_code == 404


def test_남의_검사는_못_지운다(client, other):
    _signup(client)
    _signup(other, email="lee@example.com")
    mine = _check(client).json()["check_id"]
    assert other.delete(f"/api/v1/checks/{mine}").status_code == 404
    assert client.get(f"/api/v1/checks/{mine}").status_code == 200


def test_주인_없는_검사는_아무나_못_지운다(client, other):
    """지우게 두면 **남의 결과를 아무나 지운다.**"""
    anon = _check(client).json()["check_id"]
    _signup(other, email="lee@example.com")
    assert other.delete(f"/api/v1/checks/{anon}").status_code == 404
    assert client.get(f"/api/v1/checks/{anon}").status_code == 200


# ── 저장소 고지 (헌법 4절 단서 2) ──────────────────────────────────

def test_계정_응답이_저장소_상태를_같이_싣는다(client):
    """계정이 사라질 수 있는 상태면 **화면이 그걸 말해야 한다.**"""
    body = _signup(client).json()
    assert body["storage"]["state"] in ("unknown", "persistent")
    assert "survives_restart" in body["storage"]


def test_처음_뜬_서버는_안전하다고_말하지_않는다(client):
    """확인 전에는 "안전하다"가 아니라 "확인되지 않았다"이다 (헌법 2-2)."""
    assert client.get("/api/v1/auth/me").json()["storage"]["survives_restart"] is False


# ── 무차별 대입 ────────────────────────────────────────────────────

def test_로그인_시도에_한도가_걸린다(tmp_path, monkeypatch):
    """해시가 한 번에 80ms 다 — **여기를 안 막으면 그 80ms 가 무기가 된다.**"""
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "brute.db"))
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("AUTH_LIMIT_PER_MINUTE", "3")
    import importlib

    from web import app as module

    importlib.reload(module)
    client = TestClient(module.app)

    codes = [
        client.post(
            "/api/v1/auth/login",
            json={"email": "kim@example.com", "password": f"guess-{i}-long"},
            headers={"x-forwarded-for": "203.0.113.9"},
        ).status_code
        for i in range(6)
    ]
    assert 429 in codes
    assert codes.count(401) <= 3


def test_로그인_한도가_업로드_한도와_따로_센다(tmp_path, monkeypatch):
    """한 통에 넣으면 **검사를 몇 번 돌린 사람이 로그인을 못 하게 된다.**"""
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "split.db"))
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    monkeypatch.setenv("AUTH_LIMIT_PER_MINUTE", "10")
    import importlib

    from web import app as module

    importlib.reload(module)
    client = TestClient(module.app)

    for _ in range(4):
        _check(client)  # 업로드 한도를 다 쓴다
    assert _signup(client).status_code == 201, "업로드 한도가 로그인을 막았다"


# ── CORS 가 이제 보안 경계다 ────────────────────────────────────────

def test_배포에서는_개발_주소를_닫을_수_있다(tmp_path, monkeypatch):
    """세션 쿠키가 생기기 전에는 `localhost` 를 열어 둬도 위험이 없었다.

    지금은 다르다 — 허용된 출처의 페이지는 **사용자의 쿠키를 실어** 이 API 를
    부를 수 있다. 누가 `localhost:5173` 에 악의적인 개발 서버를 띄우면
    그 페이지가 우리 배포 API 를 로그인된 채로 부른다.
    """
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "cors.db"))
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://prefab-web.onrender.com")
    monkeypatch.setenv("ALLOW_DEV_ORIGINS", "0")
    import importlib

    from web import app as module

    importlib.reload(module)
    assert "http://localhost:5173" not in module.ALLOWED_ORIGINS
    assert "https://prefab-web.onrender.com" in module.ALLOWED_ORIGINS


def test_개발_주소는_기본으로_열려_있다(tmp_path, monkeypatch):
    """예전에 `ALLOWED_ORIGINS` 가 개발 주소를 *대체*하게 만들었더니, 배포 주소를
    넣는 순간 로컬 개발이 통째로 막혔다. **별도 스위치로 둔 이유다** —
    개발하는 사람은 이 변수를 안 건드린다."""
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "cors2.db"))
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://prefab-web.onrender.com")
    monkeypatch.delenv("ALLOW_DEV_ORIGINS", raising=False)
    import importlib

    from web import app as module

    importlib.reload(module)
    assert "http://localhost:5173" in module.ALLOWED_ORIGINS
    assert "https://prefab-web.onrender.com" in module.ALLOWED_ORIGINS


def test_쿠키가_다른_출처로_실려_가게_설정돼_있다(tmp_path, monkeypatch):
    """화면과 API 가 **다른 출처**다. `SameSite=None` 이 아니면 쿠키가 안 실린다.

    그리고 `None` 은 `Secure` 없이는 브라우저가 아예 거부한다 — 둘은 같이 간다.
    기본값이 어긋나면 배포하고 나서야 "로그인이 안 된다"로 알게 된다.
    """
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "cookie.db"))
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.delenv("COOKIE_SAMESITE", raising=False)
    import importlib

    from web import app as module

    importlib.reload(module)
    assert module.COOKIE_SAMESITE == "none"
    assert module.COOKIE_SECURE is True
