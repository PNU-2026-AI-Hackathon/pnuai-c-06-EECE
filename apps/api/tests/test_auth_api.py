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

def test_로그인_없이는_검사를_못_만든다(client):
    """**8/24 팀장 결정으로 검사에 로그인 벽을 세웠다** (CLAUDE.md 4절).

    전에는 로그아웃 상태에서도 검사가 됐다. 그 전제가 바뀌었으니 여기도 바뀐다 —
    다만 **왜 막혔는지와 어떻게 푸는지**를 문구가 말해야 한다.
    """
    res = _check(client)
    assert res.status_code == 401
    err = res.json()["error"]
    assert err["code"] == "LOGIN_REQUIRED"
    assert "로그인" in err["message"]


def test_로그인해서_만든_결과는_주소를_아는_사람이_연다(client, other):
    """**공유는 그대로 열어 둔다.** 이 선이 로그인 벽의 범위다.

    링크를 받은 사람까지 가입시키면 요금표가 파는 「결과 링크 공유」가 거짓말이 되고,
    "링크 하나로 근거까지 보인다"는 최대 강점이 사라진다.
    """
    _signup(client)
    made = _check(client).json()
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


def test_없는_검사는_403_이_아니라_404_다(client):
    """403 은 **"그 ID 는 존재한다"** 를 알려 준다. 그것만으로 목록을 만들 수 있다.

    조회는 이제 로그인을 안 보므로(주소가 곧 접근 권한) 지킬 것은 이것 하나다 —
    **없는 ID 와 있는 ID 를 응답으로 구분할 수 없어야 한다.**
    """
    _signup(client)
    mine = _check(client).json()["check_id"]
    assert client.get(f"/api/v1/checks/{mine}").status_code == 200
    assert client.get("/api/v1/checks/chk_00000000000000000000000000000000").status_code == 404


def test_로그아웃해도_내가_만든_결과_링크는_열린다(client):
    """**주소가 곧 접근 권한이다.** 무료에서는 그게 공유 방식이고, 숨기지 않는다.

    비공개 링크는 요금표의 Pro 항목이다. 만들지 않았으므로 있는 척하지 않고,
    `/privacy` 가 "주소를 아는 사람은 볼 수 있습니다" 라고 그대로 적는다.
    """
    _signup(client)
    mine = _check(client).json()["check_id"]
    client.post("/api/v1/auth/logout")
    assert client.get(f"/api/v1/checks/{mine}").status_code == 200


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


def test_남의_검사는_아무나_못_지운다(client, other):
    """지우게 두면 **남의 결과를 아무나 지운다.**

    로그인 벽이 생기면서 주인 없는 검사는 더 이상 만들어지지 않는다.
    지켜야 할 것은 그대로다 — **내 것이 아니면 못 지운다.**
    """
    _signup(client)
    mine = _check(client).json()["check_id"]

    _signup(other, email="lee@example.com")
    assert other.delete(f"/api/v1/checks/{mine}").status_code == 404
    # 지우지 못했다는 것을 주인이 확인한다
    assert client.get(f"/api/v1/checks/{mine}").status_code == 200


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


# ── 문구 (헌법 11절 · 사용자에게 그대로 노출된다) ──────────────────

def test_오류_문구에_조언을_붙이지_않는다(client):
    """**"길수록 강합니다 — 기억하기 쉬운 문장을 쓰셔도 됩니다"** 가 붙어 있었다.

    그건 규칙이 아니라 우리 의견이고, 지금 뭘 해야 하는지를 안 알려준다.
    화면 쪽 안내를 고치면서 **서버 문구를 같이 안 고쳐서** 여기만 남아 있었다 —
    같은 진실이 두 곳에 있으면 한쪽만 갱신된다 (헌법 10절).
    """
    res = client.post("/api/v1/auth/signup", json={"email": "a@b.co", "password": "1234"})
    msg = res.json()["error"]["message"]

    assert "10자" in msg, msg          # 규칙은 말한다
    assert "기억하기" not in msg, msg  # 조언은 안 한다
    assert "길수록" not in msg, msg


def test_같은_이메일로_두_번_가입되지_않는다(client):
    """대소문자만 달라도 같은 사람이다. 안 그러면 한 사람이 계정을 여러 개 만든다."""
    body = {"email": "kim@example.com", "password": GOOD}
    assert client.post("/api/v1/auth/signup", json=body).status_code == 201

    again = client.post("/api/v1/auth/signup", json=body)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "EMAIL_TAKEN"

    upper = client.post(
        "/api/v1/auth/signup", json={"email": "KIM@Example.COM", "password": GOOD}
    )
    assert upper.status_code == 409, "대소문자만 다른 주소가 새 계정이 됐다"


def test_로그인_실패는_무엇이_틀렸는지_안_알려준다(client):
    """**"없는 계정입니다" 라고 하면 가입 여부를 훑어 확인할 수 있다.**

    이메일이 틀렸는지 비밀번호가 틀렸는지 가르지 않는 것이 표준이다.
    """
    _signup(client)
    wrong_pw = client.post(
        "/api/v1/auth/login", json={"email": "kim@example.com", "password": "wrong password!!"}
    )
    no_user = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": GOOD}
    )
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json()["error"] == no_user.json()["error"], "응답이 갈리면 계정 존재를 알려준다"


def test_secure_없이는_samesite_none_을_안_쓴다():
    """`SameSite=None` + `Secure` 없음 = **브라우저가 버리는 쿠키**다.

    이 조합이 나오면 서버는 200 을 주는데 화면만 로그인된 것처럼 보이고
    다음 요청부터 익명으로 간다. 증상이 로그인 버그처럼 안 생겨서 오래 걸린다.
    """
    from web.app import _samesite

    with pytest.warns(UserWarning):
        assert _samesite(secure=False, asked="none") == "lax"

    # 나머지 조합은 그대로 둔다
    assert _samesite(secure=True, asked="none") == "none"
    assert _samesite(secure=False, asked="lax") == "lax"
