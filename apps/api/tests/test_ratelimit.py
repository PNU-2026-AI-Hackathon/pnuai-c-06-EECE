"""요청 제한 — 순수한 버킷과 HTTP 층.

시계를 주입하기 때문에 **이 파일은 한 번도 잠들지 않는다.** 시간이 걸리는
테스트는 결국 지워지거나 건너뛰어진다.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from web.ratelimit import Bucket, RateLimiter, client_key

FIXTURE = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"


class FakeClock:
    """손으로 감는 단조 시계."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# ------------------------------------------------------------------ 버킷

def test_버킷은_용량만큼_주고_그_다음을_막는다():
    clock = FakeClock()
    b = Bucket(capacity=3, per_seconds=60.0)
    assert [b.take(clock()) for _ in range(4)] == [True, True, True, False]


def test_버킷은_시간이_지나면_다시_찬다():
    clock = FakeClock()
    b = Bucket(capacity=60, per_seconds=60.0)  # 초당 1개
    for _ in range(60):
        b.take(clock())
    assert b.take(clock()) is False
    clock.advance(1.0)
    assert b.take(clock()) is True


def test_남은_토큰을_소수로_들고_있는다():
    """정수로 깎으면 **시간당 한도가 영원히 안 찬다.**

    시간당 200 이면 1초에 0.055 개가 찬다. 정수로 버리면 매번 0 이 되어
    한 시간을 기다려도 한 개도 안 는다. 실제로 한 번 밟을 뻔한 자리다.
    """
    clock = FakeClock()
    b = Bucket(capacity=200, per_seconds=3600.0)
    for _ in range(200):
        b.take(clock())
    for _ in range(10):
        clock.advance(1.0)
        b.take(clock())          # 전부 실패하지만 토큰은 쌓여야 한다
    assert b.tokens > 0.5


def test_막힌_요청은_토큰을_깎지_않는다():
    clock = FakeClock()
    b = Bucket(capacity=1, per_seconds=60.0)
    b.take(clock())
    before = b.tokens
    for _ in range(50):
        b.take(clock())
    assert b.tokens == before


def test_시계가_뒤로_가도_토큰이_늘지_않는다():
    clock = FakeClock()
    b = Bucket(capacity=5, per_seconds=60.0)
    for _ in range(5):
        b.take(clock())
    clock.advance(-3600.0)
    assert b.take(clock()) is False


def test_retry_after_는_최소_1초다():
    """`Retry-After: 0` 은 즉시 재시도를 부른다 — 막으려던 것을 부른다."""
    clock = FakeClock()
    b = Bucket(capacity=1, per_seconds=60.0)
    b.take(clock())
    assert b.retry_after(clock()) >= 1


# ------------------------------------------------------------ 제한기

def test_주소마다_따로_센다():
    clock = FakeClock()
    rl = RateLimiter(per_minute=2, per_hour=100, clock=clock)
    assert rl.check("a").allowed and rl.check("a").allowed
    assert rl.check("a").allowed is False
    assert rl.check("b").allowed is True


def test_시간_한도가_분_한도보다_먼저_바닥나도_잡는다():
    clock = FakeClock()
    rl = RateLimiter(per_minute=100, per_hour=5, clock=clock)
    for _ in range(5):
        assert rl.check("a").allowed
    d = rl.check("a")
    assert d.allowed is False
    assert d.window == "시간"


def test_시간_한도에_막힌_요청이_분_한도를_깎지_않는다():
    """두 번 벌주지 않는다.

    시간 때문에 막혔는데 분 토큰까지 사라지면, 시간 창이 풀린 뒤에도
    분 창에 걸려 또 기다린다. 사용자는 왜 아직도 막히는지 알 수 없다.
    """
    clock = FakeClock()
    rl = RateLimiter(per_minute=10, per_hour=2, clock=clock)
    rl.check("a"), rl.check("a")
    minute, _ = rl._buckets("a", clock())
    left = minute.tokens
    for _ in range(5):
        rl.check("a")
    assert minute.tokens == left


def test_추적_주소_수에_상한이_있다():
    """계수 사전 자체가 공격 표면이다 — 주소를 바꿔 가며 부으면 메모리가 는다."""
    clock = FakeClock()
    rl = RateLimiter(per_minute=5, per_hour=50, clock=clock, max_clients=100)
    for i in range(1000):
        clock.advance(0.01)
        rl.check(f"10.0.0.{i}")
    assert rl.tracked <= 100


def test_오래된_주소부터_버린다():
    clock = FakeClock()
    rl = RateLimiter(per_minute=5, per_hour=50, clock=clock, max_clients=20)
    rl.check("오래된")
    for i in range(30):
        clock.advance(1.0)
        rl.check(f"새것{i}")
    assert "오래된" not in rl._clients


def test_한도가_0_이하면_거부한다():
    with pytest.raises(ValueError):
        RateLimiter(per_minute=0, per_hour=10)


# ------------------------------------------------------- 누구의 요청인가

def test_위조된_forwarded_for_로_한도를_우회할_수_없다():
    """**맨 왼쪽을 믿으면 한도가 있으나 마나다.**

    보내는 쪽이 헤더에 아무 값이나 적을 수 있다. 매 요청마다 다른 값을 적으면
    매번 새 버킷을 받는다. 맨 오른쪽은 우리 앞 프록시가 소켓에서 본 주소라
    위조가 안 된다.
    """
    seen = {client_key(f"{i}.{i}.{i}.{i}, 203.0.113.9", "10.0.0.1") for i in range(1, 50)}
    assert seen == {"203.0.113.9"}


def test_헤더가_없으면_소켓_주소를_쓴다():
    assert client_key(None, "198.51.100.4") == "198.51.100.4"


def test_열쇠가_아예_없으면_하나로_묶는다():
    """무제한으로 통과시키는 것보다 낫다 — 묶이면 서로 한도를 나눠 쓸 뿐이다."""
    assert client_key(None, None) == "unknown"


# --------------------------------------------------------------- HTTP

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from conftest import sign_in  # noqa: E402

LOCAL_ORIGIN = "http://localhost:5173"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "rl.db"))
    # **쿠키가 `Secure` 면 TestClient(http)가 버린다.** 그러면 로그인이 조용히
    # 안 되고, 검사가 401 로 막힌다 — 로그인 벽이 생기면서 실제로 그랬다.
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("ALLOWED_ORIGINS", LOCAL_ORIGIN)
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "100")
    import importlib

    from web import app as app_module

    importlib.reload(app_module)
    return TestClient(app_module.app)


def _post(client, ip="203.0.113.7", **extra):
    return client.post(
        "/api/v1/checks",
        files={"netlist": ("b.d356", FIXTURE.read_bytes(), "text/plain")},
        headers={"x-forwarded-for": ip, **extra},
    )


def test_한도를_넘으면_429_와_retry_after_를_준다(signed_in):
    for _ in range(3):
        assert _post(signed_in).status_code == 201
    r = _post(signed_in)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "RATE_LIMITED"
    assert int(r.headers["Retry-After"]) >= 1


def test_429_메시지가_언제_다시_되는지_말한다(client):
    """"너무 많습니다"만 돌려주면 새로고침을 연타하게 된다."""
    for _ in range(4):
        r = _post(client)
    message = r.json()["error"]["message"]
    assert "초 뒤에" in message


def test_429_에도_CORS_헤더가_붙는다(client):
    """붙지 않으면 화면은 "한도 초과"가 아니라 "CORS 오류"를 본다.

    미들웨어 등록 **순서**가 이걸 결정한다. 순서가 바뀌면 여기서 잡힌다.
    """
    for _ in range(4):
        r = _post(client, origin=LOCAL_ORIGIN)
    assert r.status_code == 429
    assert r.headers["access-control-allow-origin"] == LOCAL_ORIGIN


def test_다른_주소는_한도를_나눠_쓰지_않는다(signed_in):
    for _ in range(4):
        _post(signed_in, ip="203.0.113.7")
    assert _post(signed_in, ip="198.51.100.2").status_code == 201


def test_통과한_응답은_남은_횟수를_알려준다(client):
    r = _post(client)
    assert int(r.headers["X-RateLimit-Remaining"]) == 2


def test_결과_조회는_제한하지_않는다(signed_in):
    """공유된 링크를 여는 것까지 막으면 안 된다 — 그건 비싼 일이 아니다."""
    check_id = _post(signed_in).json()["check_id"]
    for _ in range(30):
        assert signed_in.get(f"/api/v1/checks/{check_id}").status_code == 200


def test_본문이_상한을_넘으면_읽기_전에_끊는다(client):
    """핸들러까지 가면 이미 파일을 다 받은 뒤다 — 막으려던 비용을 이미 치렀다."""
    r = client.post(
        "/api/v1/checks",
        content=b"x" * 100,
        headers={"content-length": str(64 * 1024 * 1024)},
    )
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_업로드는_디스크로_넘어가지_않는다(client):
    """화면에 "디스크에 쓰지 않습니다"라고 적어 뒀다. **그게 참이어야 한다.**

    starlette 기본값은 1MB 를 넘으면 임시 파일로 넘긴다. 우리 상한은 10MB 라
    그 사이 크기는 조용히 디스크에 쓰였다. 고지가 코드보다 앞서 있었다.
    """
    rolled: list[int] = []
    original = tempfile.SpooledTemporaryFile.rollover

    def spy(self):
        rolled.append(1)
        return original(self)

    tempfile.SpooledTemporaryFile.rollover = spy
    try:
        client.post(
            "/api/v1/checks",
            files={"netlist": ("big.d356", b"C  \n" + b"X" * 3 * 1024 * 1024, "text/plain")},
        )
    finally:
        tempfile.SpooledTemporaryFile.rollover = original
    assert rolled == []


def test_한도를_끌_수_있다(tmp_path, monkeypatch):
    """시연 중에 한도가 걸리는 것만큼 나쁜 사고가 없다."""
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "off.db"))
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "0")
    import importlib

    from web import app as app_module

    importlib.reload(app_module)
    c = TestClient(app_module.app)
    sign_in(c)  # 검사를 만들려면 로그인해야 한다 (8/24)
    for _ in range(5):
        assert _post(c).status_code == 201
