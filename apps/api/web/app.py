"""FastAPI 어댑터.

이 파일에는 판정도 검증 규칙도 없다. 전부 service.py 에 있다.
여기가 하는 일은 HTTP ↔ dict 변환뿐이다.
"""

from __future__ import annotations

import os
import warnings

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.formparsers import MultiPartParser

from prefab.datasheet.store import FactStore

from . import apikeys, badge, github, guest, quota, repo, service, storage, usage, waitlist
from .auth import AuthError, AuthStore, normalize_email
from .ratelimit import RateLimiter, client_key
from .service import ApiError

# --------------------------------------------------------------------- 설정

#: 개발 포트는 **항상** 열어 둔다.
#:
#: 5173 만 열면 안 된다 — vite 는 5173 이 점유돼 있으면 **말없이 5174 로 올린다.**
#: 그러면 CORS 가 조용히 막히고 화면은 이유를 모른 채 기능을 잃는다. 실제로 한 번 밟았다.
DEV_PORTS = (5173, 5174, 5175)
DEV_ORIGINS = [
    f"http://{host}:{port}" for port in DEV_PORTS for host in ("localhost", "127.0.0.1")
]

#: 배포 주소는 `ALLOWED_ORIGINS` 로 **더한다. 대체하지 않는다.**
#:
#: 대체하게 만들었더니 Render 에 배포 주소를 넣는 순간 로컬 개발이 통째로 막혔다.
#: 증상이 고약하다 — 화면은 멀쩡히 뜨고 검사만 조용히 실패한다. 배포한 사람은
#: 자기가 무엇을 껐는지 모르고, 다른 사람은 자기 코드를 의심한다.
#:
#: **이 주석은 8/23 에 틀린 것이 됐다. 고쳐서 남긴다.**
#:
#: 원래 이렇게 적혀 있었다 — *"여기서 CORS 는 보안 경계가 아니다. 이 API 는
#: 인증이 없어서 `curl` 로는 어차피 누구나 부른다. 개발 포트를 더 여는 것으로
#: 늘어나는 위험이 없다."* 인증이 없던 동안에는 맞는 말이었다.
#:
#: **세션 쿠키가 생기면서 CORS 가 보안 경계가 됐다.** 이제 허용된 출처의
#: 페이지는 사용자의 쿠키를 실어 이 API 를 부를 수 있다. `curl` 은 쿠키가
#: 없으니 상관없지만, 브라우저는 다르다.
#:
#: 그래서 **개발 주소를 배포에서는 닫는다.** 누가 `localhost:5173` 에 악의적인
#: 개발 서버를 띄우면(예를 들어 남의 프로젝트를 받아 `npm run dev` 하면)
#: 그 페이지가 우리 배포 API 를 로그인된 채로 부를 수 있다. 확률은 낮지만
#: 공짜로 막을 수 있는 것을 열어 둘 이유가 없다.
#:
#: **끄는 스위치를 따로 둔 이유가 있다.** 예전에 `ALLOWED_ORIGINS` 를 설정하면
#: 개발 주소가 *대체*되게 만들었더니, 배포 주소를 넣는 순간 로컬 개발이 통째로
#: 막혔다. 증상이 고약했다 — 화면은 멀쩡히 뜨고 검사만 조용히 실패한다.
#: 별도 변수로 두면 **배포에서만 켜고, 개발하는 사람은 아무것도 안 건드린다.**
ALLOW_DEV_ORIGINS = os.getenv("ALLOW_DEV_ORIGINS", "1") not in ("0", "false", "False")

ALLOWED_ORIGINS = (DEV_ORIGINS if ALLOW_DEV_ORIGINS else []) + [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()
]

#: Vercel 프리뷰 배포는 URL 이 매번 바뀐다. 정규식으로 함께 허용한다.
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX", r"https://.*\.vercel\.app")

DB_PATH = os.getenv("PREFAB_DB", "prefab.db")

#: 검사 업로드의 주소별 한도.
#:
#: 검사 자체는 밀리초지만 업로드는 파일을 받아 파싱하는 동안 워커를 붙잡는다.
#: 사람이 손으로 쓰는 속도(한 보드 올리고 결과를 읽는 데 몇 분)와는 두 자릿수
#: 차이라 **정상 사용에는 절대 닿지 않는 값**으로 뒀다. 닿는다면 그건 사람이
#: 아니거나, 우리가 쓰는 법을 잘못 안 것이다 — 후자면 이 숫자를 올릴 일이다.
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "200"))

#: 끌 수 있게 둔다. 시연 중에 한도가 걸리는 것만큼 나쁜 사고가 없다.
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "1") not in ("0", "false", "False")

#: 로그인 시도의 주소별 한도. **업로드보다 훨씬 빡빡하다.**
#:
#: 비밀번호 해시가 한 번에 80ms 쯤 걸리는데, 그건 무차별 대입에 벽이면서
#: 동시에 **워커를 붙잡는 수단**이기도 하다. 사람이 로그인하는 속도와는
#: 두 자릿수 차이라 정상 사용에는 닿지 않는다.
AUTH_LIMIT_PER_MINUTE = int(os.getenv("AUTH_LIMIT_PER_MINUTE", "10"))
AUTH_LIMIT_PER_HOUR = int(os.getenv("AUTH_LIMIT_PER_HOUR", "60"))

#: 세션 쿠키 이름과 속성.
#:
#: 화면(`prefab-web.onrender.com`)과 API(`...prefab.onrender.com`)가 **다른
#: 출처**라서 `SameSite=None` 이어야 쿠키가 실려 간다. 그리고 `None` 은
#: `Secure` 없이는 브라우저가 아예 거부한다. 둘은 같이 간다.
#:
#: `HttpOnly` 는 양보하지 않는다. 토큰을 `localStorage` 에 두면 스크립트가
#: 읽을 수 있고, 그러면 XSS 한 번이 곧 계정 탈취가 된다.
SESSION_COOKIE = "prefab_session"

#: GitHub 을 다녀오는 동안 「어디로 돌아갈지」를 나르는 쿠키. 10분 살고 지워진다.
GITHUB_NEXT_COOKIE = "prefab_github_next"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "1") not in ("0", "false", "False")


def _samesite(secure: bool, asked: str) -> str:
    """`SameSite` 를 정한다 — **`Secure` 와 어긋나지 못하게.**

    둘을 각각 환경변수로 받으면 반드시 어긋나는 날이 온다. 그리고 어긋난
    쿠키(`SameSite=None` 인데 `Secure` 없음)는 **브라우저가 저장조차 하지
    않는다.** 서버는 200 을 주고 화면은 로그인된 것처럼 그려지는데, 다음
    요청부터 익명으로 간다 — 로컬 개발에서 이 조합으로 한 번 당했다.

    그래서 `Secure` 가 꺼져 있으면(로컬 http) `lax` 로 내린다. 로컬은
    5173 과 8000 이 **포트만 다른 같은 site** 라서 `lax` 로도 실려 간다.
    """
    if asked == "none" and not secure:
        # 조용히 내리지 않는다 — 배포에서 이걸 보면 설정이 틀린 것이다
        warnings.warn(
            "COOKIE_SECURE 가 꺼져 있어 SameSite 를 none → lax 로 내렸습니다. "
            "none 은 Secure 없이는 브라우저가 쿠키를 버립니다.",
            stacklevel=2,
        )
        return "lax"
    return asked


COOKIE_SAMESITE = _samesite(COOKIE_SECURE, os.getenv("COOKIE_SAMESITE", "none"))

#: 멀티파트를 **메모리에만** 둔다.
#:
#: starlette 기본값은 1MB 를 넘으면 임시 파일로 넘긴다(`SpooledTemporaryFile`).
#: 우리는 상한이 10MB 라서, 1~10MB 파일은 우리가 모르는 사이에 디스크에 쓰였다.
#: 화면에는 "디스크에 쓰지 않습니다"라고 적어 두고서. **고지가 코드보다 앞서
#: 있었다** (헌법 2-4). 상한 위로 올려서 문구가 참이 되게 한다.
#:
#: 메모리를 대신 쓰는데, 본문 크기는 아래 미들웨어가 읽기 전에 끊고 동시 요청
#: 수는 요청 제한이 누른다.
MultiPartParser.spool_max_size = service.MAX_UPLOAD_BYTES + 1
MultiPartParser.max_part_size = service.MAX_UPLOAD_BYTES + 1

limiter = RateLimiter(per_minute=RATE_LIMIT_PER_MINUTE, per_hour=RATE_LIMIT_PER_HOUR)

#: 로그인 시도는 업로드와 **따로** 센다. 한 통에 넣으면 검사를 몇 번 돌린
#: 사람이 로그인을 못 하게 된다.
auth_limiter = RateLimiter(per_minute=AUTH_LIMIT_PER_MINUTE, per_hour=AUTH_LIMIT_PER_HOUR)

app = FastAPI(title="Prefab API", version="0.1.0", docs_url="/docs")


# 이 미들웨어는 **CORS 보다 먼저 등록한다.** starlette 은 나중에 등록한 것을
# 바깥에 두기 때문에, 순서를 바꾸면 429 응답이 CORS 를 못 거친다. 그러면
# 브라우저는 "한도 초과"가 아니라 "CORS 오류"를 보고, 화면은 이유를 잃는다.
@app.middleware("http")
async def guard(request: Request, call_next):
    """본문을 읽기 **전에** 크기와 한도를 본다.

    핸들러 안에서 검사하면 이미 늦다 — 그때는 멀티파트 파서가 파일을 다 받아
    메모리에 올려 둔 뒤다. 막으려던 비용을 이미 치른 것이다.
    """
    path = request.url.path
    # **대기 명단도 여기서 막는다.** 남의 이메일을 대신 넣어 명단을 오염시키는
    # 장난이 제일 쉬운 자리이고, 그 숫자가 곧 우리 수요 판단 근거다.
    guarded = (
        path.startswith("/api/v1/checks")
        or path.startswith("/api/v1/auth/")
        or path.startswith("/api/v1/waitlist")
        # **데이터시트 요청은 우리 돈이 나가는 유일한 자리다** (실측 약 $0.03/부품).
        # 월 할당량이 이미 막고 있지만, 그건 계정 단위다. 계정을 여러 개 만들어
        # 두드리는 것까지는 못 막으므로 주소 단위 한도를 겹쳐 둔다.
        or path.startswith("/api/v1/parts/")
    )
    if request.method != "POST" or not guarded:
        return await call_next(request)

    # 로그인·가입은 업로드와 다른 통으로 센다. 해시 한 번이 80ms 라
    # 여기를 안 막으면 비밀번호를 지키려고 고른 값이 서비스를 눕히는 수단이 된다.
    bucket = auth_limiter if path.startswith("/api/v1/auth/") else limiter

    declared = request.headers.get("content-length")
    if (
        path.startswith("/api/v1/checks")
        and declared
        and declared.isdigit()
        and int(declared) > service.MAX_UPLOAD_BYTES
    ):
        err = service.body_too_large()
        return JSONResponse(status_code=err.status, content=err.to_dict())

    if not RATE_LIMIT_ENABLED:
        return await call_next(request)

    key = client_key(request.headers.get("x-forwarded-for"), _peer(request))
    decision = bucket.check(key)
    if not decision.allowed:
        err = service.too_many_requests(decision.window, decision.retry_after)
        return JSONResponse(
            status_code=err.status,
            content=err.to_dict(),
            headers={
                "Retry-After": str(decision.retry_after),
                "X-RateLimit-Limit": str(RATE_LIMIT_PER_MINUTE),
                "X-RateLimit-Remaining": "0",
            },
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_PER_MINUTE)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
    return response


def _peer(request: Request) -> str | None:
    return request.client.host if request.client else None

# CORS 는 첫 커밋에 넣는다. 배포 직전에 발견하면 반나절이 날아간다.
# POST /api/v1/checks 는 multipart 라 OPTIONS 프리플라이트가 먼저 온다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    # 세션 쿠키가 다른 출처로 실려 가려면 이게 있어야 한다.
    # **이걸 켜면 `allow_origins` 에 `*` 를 쓸 수 없다** — 브라우저가 거부한다.
    # 우리는 처음부터 목록으로 적어 왔으니 그대로 간다.
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,
)

store = service.Store(DB_PATH)

#: 업로드 없이 볼 수 있는 실측 보드 결과 하나 (F-4).
#: 넣지 못하면 None 이 되고, 루트 응답에서도 빠진다 — 있는 척하지 않는다.
SAMPLE_CHECK_ID = service.seed_sample(store)
#: 부품 사실 DB. **checks 와 같은 파일**을 쓴다 — SQLite 한 개 (CLAUDE.md 9절).
facts = FactStore(DB_PATH)

#: 계정·세션. **checks 와 같은 파일**을 쓴다 (헌법 9절).
accounts = AuthStore(DB_PATH)

#: 이 저장소가 재시작을 견디는지 **재서** 안다. 기동 때 한 번만 부른다.
#: 무료 플랜에는 영구 디스크를 못 붙여서 계정이 재배포마다 사라질 수 있는데,
#: 그걸 조용히 두지 않으려고 만든 것이다 (헌법 4절 단서 2).
STORAGE = storage.probe(DB_PATH)

#: GitHub 로그인 설정. **켜지지 않았으면 없는 기능이다** —
#: 화면이 `enabled` 를 보고 버튼을 아예 안 그린다 (헌법 2-4).
GITHUB = github.config_from_env()

#: 커밋된 사실 파일을 기동 때 심는다. 배포 이미지에는 DB 가 없기 때문이다 —
#: 안 심으면 데이터시트 해제가 배포된 서버에서만 조용히 사라진다.
#: 이 덕분에 **영구 디스크가 필요 없다.** 못 심으면 빈 목록이고, 루트 응답에 그대로 실린다.
SEEDED_PARTS = service.seed_facts(os.getenv("PREFAB_PARTS", "parts"), facts)

#: 심사위원·구경꾼용 공용 계정. **기동 때마다 심는다.**
#:
#: README 가 이 계정을 적어 두고 있다. 그런데 무료 플랜이라 재배포마다 DB 가
#: 비워져서, **적어 둔 계정이 안 되는 상태가 실제로 있었다** — 8/26 에 로그인해
#: 보니 401 이었다. 문서에 적힌 것이 거짓이 되는 자리라 코드가 지키게 한다.
#:
#: **비밀이 아니다.** README 에 공개된 값이고 그래서 저장소에 그대로 적는다.
#: 숨겨야 할 값이라면 여기 있으면 안 되고, 여기 있어도 되는 값이라 여기 있다.
DEMO_EMAIL = os.getenv("DEMO_EMAIL", "review@prefab.demo")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "prefab-review-2026")


def _seed_demo_account() -> bool:
    """공용 계정이 없으면 만든다. 있으면 아무것도 안 한다.

    **실패해도 서버는 뜬다.** 구경용 계정 하나 때문에 서비스가 안 뜨면 그게 더 나쁘다.
    """
    try:
        accounts.authenticate(DEMO_EMAIL, DEMO_PASSWORD)
        return True
    except Exception:
        pass
    try:
        accounts.create_user(DEMO_EMAIL, DEMO_PASSWORD)
        return True
    except Exception:
        return False


DEMO_ACCOUNT_READY = _seed_demo_account()


# --------------------------------------------------------------------- 오류

@app.exception_handler(ApiError)
async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content=exc.to_dict())


@app.exception_handler(AuthError)
async def auth_error_handler(_request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    err = service.internal_error()
    return JSONResponse(status_code=err.status, content=err.to_dict())


# --------------------------------------------------------------------- 라우트

@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict:
    """서비스 안내. 계약에 없는 엔드포인트라 여기서만 샘플 ID 를 알려준다."""
    out = {"service": "prefab-api", "docs": "/docs", "contract": "/api/v1/rules"}
    if SAMPLE_CHECK_ID:
        # 프론트가 이 값을 읽어 "업로드 없이 예시 보기" 를 띄운다 (F-4).
        out["sample_check"] = f"/api/v1/checks/{SAMPLE_CHECK_ID}"
    # 몇 개를 심었는지 그대로 싣는다. 0 이면 데이터시트 해제가 안 도는 상태다 (헌법 2-4).
    out["seeded_parts"] = SEEDED_PARTS
    # **심었다고 말하지 않고 실제로 되는지 말한다.** 여기가 거짓이면 README 도 거짓이다.
    out["demo_account"] = DEMO_EMAIL if DEMO_ACCOUNT_READY else None
    return out


# ------------------------------------------------------------------- 인증

def _current_user(request: Request):
    """세션 쿠키로 사용자를 찾는다. 없으면 `None`.

    **없다고 거절하지 않는다.** 로그아웃 상태에서도 검사가 되고 결과가 열려야
    하기 때문이다 (헌법 4절 단서 1). 거절이 필요한 자리에서만 따로 거절한다.
    """
    # **키를 쿠키보다 먼저 본다.** 둘 다 있으면 명시적으로 준 쪽이 뜻이다 —
    # CI 러너가 쿠키를 들고 있을 일은 없지만, 사람이 브라우저에서 키를 시험할 때
    # 로그인된 자기 계정으로 조용히 도는 것보다 키가 이기는 편이 덜 헷갈린다.
    bearer = _bearer(request)
    if apikeys.looks_like_key(bearer):
        with store.session() as conn:
            user_id = apikeys.user_for(conn, bearer)
        return accounts.find_user(user_id) if user_id else None

    return accounts.user_for_token(request.cookies.get(SESSION_COOKIE))


def _bearer(request: Request) -> str | None:
    """`Authorization: Bearer prefab_...` 에서 키를 꺼낸다.

    쿼리스트링으로는 안 받는다 — 주소는 서버 로그·브라우저 기록·리퍼러에
    그대로 남는다. 키는 그런 데 남으면 안 된다.
    """
    raw = request.headers.get("authorization") or ""
    scheme, _, value = raw.partition(" ")
    return value.strip() if scheme.lower() == "bearer" else None


def _require_user(request: Request):
    user = _current_user(request)
    if user is None:
        raise AuthError("NOT_AUTHENTICATED", "로그인이 필요합니다.", 401)
    return user


def _with_session(body: dict, token: str, expires, status: int = 200) -> JSONResponse:
    # `JSONResponse` 를 직접 돌려주면 데코레이터의 `status_code` 가 무시된다.
    # 가입이 201 대신 200 으로 나가는 걸 테스트에서 잡았다.
    response = JSONResponse(content=body, status_code=status)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        expires=expires,
        path="/",
    )
    return response


def _account_body(user) -> dict:
    """계정 응답. **여기에 실리는 것이 우리가 가진 전부다.**

    비밀번호 해시는 물론이고 세션 토큰도 안 싣는다. 저장소 상태를 같이
    싣는 이유는, 계정이 사라질 수 있는 상태라면 **화면이 그걸 말해야** 하기
    때문이다 (헌법 4절 단서 2).
    """
    return {
        "email": user.email,
        "created_at": user.created_at,
        "storage": STORAGE.to_dict(),
    }


@app.post("/api/v1/auth/signup", status_code=201)
async def signup(payload: dict) -> JSONResponse:
    email = normalize_email(str(payload.get("email", "")))
    password = str(payload.get("password", ""))
    user = accounts.create_user(email, password)
    token, expires = accounts.open_session(user.id)
    return _with_session(_account_body(user), token, expires, status=201)


@app.post("/api/v1/auth/login")
async def login(payload: dict) -> JSONResponse:
    email = normalize_email(str(payload.get("email", "")))
    password = str(payload.get("password", ""))
    user = accounts.authenticate(email, password)
    token, expires = accounts.open_session(user.id)
    return _with_session(_account_body(user), token, expires)


@app.post("/api/v1/auth/logout")
async def logout(request: Request) -> JSONResponse:
    accounts.close_session(request.cookies.get(SESSION_COOKIE))
    response = JSONResponse(content={"ok": True})
    # 만료만 시키지 않고 **지운다.** 만료된 쿠키가 남아 있으면 다음 요청에
    # 그대로 실려 가고, 서버는 매번 세션을 찾다 실패한다.
    response.delete_cookie(
        SESSION_COOKIE, path="/", httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE
    )
    return response


# ------------------------------------------------------- GitHub 으로 로그인
#
# **두 엔드포인트 모두 브라우저가 주소창으로 오는 자리다.** fetch 가 아니다.
# 그래서 오류를 JSON 으로 돌려주면 사용자는 화면에 날 JSON 을 보게 된다.
# 대신 화면의 로그인 페이지로 사유를 붙여 되돌린다.


def _github_off():
    return ApiError(
        "GITHUB_DISABLED",
        "이 서버에는 GitHub 로그인이 설정되어 있지 않습니다.",
        404,
    )


@app.get("/api/v1/auth/github/start")
async def github_start(request: Request):
    """GitHub 승인 화면으로 보낸다."""
    if not GITHUB.enabled:
        raise _github_off()

    state = github.new_state(GITHUB.client_secret)
    response = RedirectResponse(github.authorize_url(GITHUB, state), status_code=302)
    # **돌아갈 곳을 state 에 안 싣는다.** state 는 서명해서 위조를 막는 값이고,
    # 거기에 사용자 입력을 섞으면 검증 대상이 늘어난다. 짧게 사는 쿠키로 따로 나른다.
    response.set_cookie(
        GITHUB_NEXT_COOKIE,
        github.safe_next(request.query_params.get("next")),
        max_age=github.STATE_TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    return response


@app.get("/api/v1/auth/github/callback")
async def github_callback(request: Request):
    """GitHub 이 돌려보낸 자리. 여기서 세션 쿠키가 심긴다."""
    if not GITHUB.enabled:
        raise _github_off()

    landing = github.safe_next(request.cookies.get(GITHUB_NEXT_COOKIE))

    def back(code: str) -> RedirectResponse:
        """로그인 화면으로 사유를 달아 돌려보낸다."""
        response = RedirectResponse(f"{GITHUB.web_base}/login?error={code}", status_code=302)
        response.delete_cookie(GITHUB_NEXT_COOKIE, path="/")
        return response

    # 사용자가 GitHub 화면에서 「취소」를 누른 경우다. 오류가 아니다.
    if request.query_params.get("error"):
        return back("cancelled")

    try:
        github.check_state(GITHUB.client_secret, request.query_params.get("state"))
        code = request.query_params.get("code") or ""
        if not code:
            raise github.GithubError("EXCHANGE_FAILED", "")
        access = github.exchange_code(GITHUB, code)
        identity = github.fetch_identity(access)
        user = accounts.link_or_create_github(
            identity.github_id, identity.login, identity.email
        )
    except github.GithubError as failure:
        return back(failure.code.lower())
    except AuthError as failure:
        return back(failure.code.lower())

    token, expires = accounts.open_session(user.id)
    response = RedirectResponse(f"{GITHUB.web_base}{landing}", status_code=302)
    # 저장소 연동으로 돌아온 흐름이면 접근 토큰을 짧게 사는 쿠키로 넘긴다.
    # **DB 에 안 넣는다** — 위 「토큰을 저장하지 않는다」 참고.
    if landing == "/connect":
        response.set_cookie(
            CONNECT_COOKIE, access, max_age=CONNECT_TTL_SECONDS,
            httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, path="/",
        )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        expires=expires,
        path="/",
    )
    response.delete_cookie(GITHUB_NEXT_COOKIE, path="/")
    return response


# ------------------------------------------------------------ 저장소 연동
#
# ## 토큰을 저장하지 않는다
#
# 연동은 **한 번 하는 일**이다. 그래서 권한을 받아 그 흐름 안에서만 쓰고 버린다.
# 저장하면 우리 DB 가 남의 **비공개 회로도 저장소 열쇠**를 들고 있게 되는데,
# 지금 우리에게는 그걸 지킬 암호화도, 애초에 살아남는 저장소도 없다.
#
# 대신 짧게 사는 쿠키로 나른다 — 브라우저가 들고 있다가 흐름이 끝나면 지워진다.
# 서버가 재배포돼도 진행 중인 연동이 안 끊긴다는 덤도 있다.

#: 연동 흐름 동안만 사는 쿠키. **여기 담긴 것은 GitHub 접근 토큰이다.**
CONNECT_COOKIE = "prefab_gh_connect"

#: 그 쿠키의 수명. 저장소 고르고 파일 확인하는 데 드는 시간 + 여유.
CONNECT_TTL_SECONDS = 900


def _connect_token(request: Request) -> str:
    token = request.cookies.get(CONNECT_COOKIE)
    if not token:
        raise ApiError(
            "NOT_CONNECTED",
            "저장소 연결이 만료되었습니다. 다시 연결해 주세요.",
            401,
        )
    return token


def _drop_connect(response):
    """토큰 쿠키를 지운다. **끝났으면 바로 버린다.**"""
    response.delete_cookie(CONNECT_COOKIE, path="/")
    return response


@app.get("/api/v1/github/connect/start")
async def connect_start(request: Request):
    """저장소 권한을 물어보는 승인 화면으로 보낸다. 로그인과 **다른 scope** 다."""
    if not GITHUB.enabled:
        raise _github_off()
    _require_user(request)
    state = github.new_state(GITHUB.client_secret)
    response = RedirectResponse(github.connect_url(GITHUB, state), status_code=302)
    # 로그인 흐름과 콜백이 같아서, 어느 쪽인지 표식을 남긴다.
    response.set_cookie(
        GITHUB_NEXT_COOKIE, "/connect", max_age=github.STATE_TTL_SECONDS,
        httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, path="/",
    )
    return response


@app.get("/api/v1/github/repos")
async def list_repos(request: Request) -> dict:
    """쓸 수 있는 저장소 목록. **`push` 권한이 있는 것만.**"""
    _require_user(request)
    return {"repos": [r.to_dict() for r in github.list_repos(_connect_token(request))]}


@app.get("/api/v1/github/scan")
async def scan_repo(request: Request) -> dict:
    """저장소를 훑어 넷리스트·펌웨어·부품목록 후보를 찾는다.

    **고르지 않는다. 후보를 근거와 함께 늘어놓는다** (`web/repo.py`).
    """
    _require_user(request)
    full_name = (request.query_params.get("repo") or "").strip()
    branch = (request.query_params.get("branch") or "main").strip()
    if not full_name:
        raise ApiError("BAD_REQUEST", "저장소를 골라 주세요.", 422)

    paths, truncated = github.list_paths(_connect_token(request), full_name, branch)
    found = repo.scan(paths).to_dict()
    return {
        "repo": full_name,
        "branch": branch,
        "files_seen": len(paths),
        # **잘렸으면 말한다.** 이걸 숨기면 "넷리스트가 없습니다" 가 거짓이 된다.
        "truncated": truncated,
        **found,
    }


@app.post("/api/v1/github/setup")
async def setup_repo(request: Request, payload: dict) -> JSONResponse:
    """워크플로 파일을 넣는 PR 을 연다. **기본 브랜치에 직접 안 쓴다.**"""
    _require_user(request)
    full_name = str(payload.get("repo") or "").strip()
    branch = str(payload.get("branch") or "main").strip()
    netlist = str(payload.get("netlist") or "").strip()
    if not full_name or not netlist:
        raise ApiError("BAD_REQUEST", "저장소와 넷리스트 경로가 필요합니다.", 422)

    url = github.open_setup_pr(
        _connect_token(request),
        full_name,
        branch,
        repo.WORKFLOW_PATH,
        repo.workflow_yaml(
            netlist,
            str(payload.get("firmware") or "").strip() or None,
            str(payload.get("bom") or "").strip() or None,
        ),
    )
    # **일이 끝났으니 토큰을 버린다.** 더 들고 있을 이유가 없다.
    return _drop_connect(JSONResponse({"pull_request": url, "path": repo.WORKFLOW_PATH}))


@app.get("/api/v1/checks/{check_id}/badge.svg")
async def check_badge(check_id: str) -> Response:
    """검사 결과를 배지 하나로. **남의 README 에 붙는다.**

    ## 로그인을 요구하지 않는다

    README 는 로그인 안 한 사람도 본다. 배지가 안 뜨면 그 저장소가 깨져 보인다.
    배지에 실리는 것은 **숫자 두 개뿐**이고, 그건 이미 결과 링크가 공개하는 값이다.

    ## 비공개 검사도 숫자는 준다

    주인이 비공개로 바꿨어도 배지는 뜬다 — 배지에는 회로도도 코드도 안 실린다.
    **내용은 안 주고 상태만 준다.** 그래야 비공개로 두면서도 배지를 쓸 수 있다.

    ## 못 찾아도 500 을 내지 않는다

    없는 검사면 회색 「검사 없음」을 돌려준다. README 에 깨진 이미지가 뜨는 것보다
    **모른다고 적힌 배지**가 낫다 (헌법 2-2).
    """
    try:
        result = store.get(check_id)
        summary = result.get("summary") or {}
        right, color = badge.summarize(
            int(summary.get("critical") or 0), int(summary.get("warning") or 0)
        )
    except Exception:
        right, color = badge.unknown()

    return Response(
        badge.render(right, color),
        media_type="image/svg+xml",
        headers={
            # **짧게 둔다.** GitHub 이 자기 프록시로 캐시하는데, 길면 고쳐진 뒤에도
            # 며칠씩 빨간 배지가 남는다. 틀린 배지는 없느니만 못하다.
            "Cache-Control": "max-age=60, s-maxage=60",
        },
    )


@app.get("/api/v1/auth/me")
async def me(request: Request) -> dict:
    """로그인 상태. **로그인 안 했으면 401 이 아니라 `user: null` 이다.**

    화면이 뜨자마자 부르는 자리라, 로그아웃 상태를 오류로 만들면 콘솔이
    401 로 가득 차고 진짜 오류가 그 사이에 묻힌다.
    """
    user = _current_user(request)
    return {
        "user": _account_body(user) if user else None,
        "storage": STORAGE.to_dict(),
        # 화면이 「GitHub 으로 시작하기」를 그릴지 정하는 유일한 근거다.
        # 서버가 못 하는 일을 버튼으로 만들어 두지 않는다.
        "github": {"enabled": GITHUB.enabled},
        # 로그인 안 한 사람이 몇 번 더 써 볼 수 있는가.
        # **화면이 이 숫자를 지어내면 안 된다** — 쿠키는 httpOnly 라 못 읽는다.
        "guest": {
            "remaining": guest.remaining(request.cookies.get(guest.COOKIE)) if user is None else 0,
            "free": guest.FREE_CHECKS,
        },
    }


@app.get("/api/v1/checks/mine")
async def my_checks(request: Request) -> dict:
    user = _require_user(request)
    return {"checks": store.list_for_owner(user.id)}


@app.get("/api/v1/usage")
async def usage_stats() -> dict:
    """이 서버의 실측 사용량. **요금 안내 화면이 여기서 숫자를 가져간다.**

    화면에 숫자를 손으로 적지 않으려고 만든 엔드포인트다. 손으로 적으면
    반드시 낡고, 낡은 숫자는 없는 것보다 나쁘다.

    검사 수는 **배포할 때마다 0 부터 다시 센다** — 영구 디스크가 없기 때문이다.
    부품·사실 수는 커밋된 파일에서 기동 때 다시 심으므로 배포와 무관하다.
    이 차이를 화면도 그대로 말한다 (헌법 2-4).
    """
    return usage.collect(DB_PATH).to_dict()


@app.post("/api/v1/waitlist", status_code=201)
async def join_waitlist(request: Request) -> dict:
    """출시 알림 대기 명단.

    **결제를 만들기 전에 살 사람이 있는지 재는 자리다.** 요금표가 「준비 중」이라고만
    적혀 있는 동안은 방문자가 반응할 대상이 없어서, 비싼지 싼지조차 알 수 없다.

    받는 것은 **이메일 하나뿐**이다. 이름·소속·전화번호는 물어볼 이유가 없다.
    """
    body = await request.json()
    if not isinstance(body, dict):
        raise ApiError("BAD_REQUEST", "요청 본문이 올바르지 않습니다.", 400)

    try:
        with store.session() as conn:
            waitlist.join(conn, str(body.get("email") or ""), str(body.get("plan") or ""))
    except waitlist.WaitlistError as exc:
        raise ApiError(exc.code, exc.message, 400) from exc

    # **몇 명인지는 안 돌려준다.** 대기 인원은 우리 내부 지표이고,
    # 화면에 "3명 대기 중" 같은 숫자가 뜨면 오히려 안 팔리는 제품처럼 보인다.
    return {"joined": True}


@app.get("/api/v1/keys")
async def list_keys(request: Request) -> dict:
    user = _current_user(request)
    if user is None:
        raise ApiError("LOGIN_REQUIRED", "로그인이 필요합니다.", 401)
    with store.session() as conn:
        return {"keys": apikeys.list_for(conn, user.id), "max": apikeys.MAX_KEYS_PER_USER}


@app.post("/api/v1/keys", status_code=201)
async def create_key(request: Request) -> dict:
    """키를 만든다. **원문은 이 응답에만 실린다** — 다시는 못 본다.

    DB 에는 SHA-256 만 남는다 (세션 토큰과 같은 규칙). 그래서 잃어버리면
    되찾을 수 없고, 화면이 그 사실을 만들기 전에 미리 말해야 한다.
    """
    user = _current_user(request)
    if user is None:
        raise ApiError("LOGIN_REQUIRED", "로그인이 필요합니다.", 401)
    body = await request.json()
    try:
        with store.session() as conn:
            key, token = apikeys.create(conn, user.id, str((body or {}).get("label") or ""))
    except apikeys.ApiKeyError as exc:
        raise ApiError(exc.code, exc.message, 400) from exc
    return {**key.to_dict(), "token": token}


@app.delete("/api/v1/keys/{key_id}")
async def revoke_key(key_id: str, request: Request) -> dict:
    user = _current_user(request)
    if user is None:
        raise ApiError("LOGIN_REQUIRED", "로그인이 필요합니다.", 401)
    with store.session() as conn:
        if not apikeys.revoke(conn, user.id, key_id):
            raise ApiError("KEY_NOT_FOUND", "그런 키가 없습니다.", 404)
    return {"revoked": key_id}


@app.get("/api/v1/parts/quota")
async def get_quota(request: Request) -> dict:
    """이번 달 남은 데이터시트 읽기 요청.

    **화면이 버튼을 누르기 전에 남은 수를 보여줘야 한다.** 눌러 보고 나서
    "다 쓰셨습니다" 라고 하면 그건 알려준 게 아니라 막은 것이다.
    """
    user = _current_user(request)
    if user is None:
        raise ApiError("LOGIN_REQUIRED", "로그인하시면 남은 요청 수를 볼 수 있습니다.", 401)
    with store.session() as conn:
        return quota.quota_of(conn, user.id).to_dict()


@app.post("/api/v1/parts/{mpn}/request", status_code=201)
async def request_datasheet(mpn: str, request: Request) -> dict:
    """아직 안 읽은 부품의 데이터시트를 읽어 달라고 남긴다.

    **검사는 무제한 무료다.** 판정이 순수 함수라 원가가 0이기 때문이다.
    돈이 나가는 자리는 여기 하나뿐이라 (실측 약 $0.03/부품) 여기만 센다.

    **이미 읽은 부품은 할당량을 안 쓴다.** `part_facts` 는 공용이라 두 번째
    요청부터 원가가 0이다. 그 사실을 `status: "known"` 으로 그대로 돌려준다.

    큐에 들어간 요청은 **사람이 보고 처리한다** (헌법 2-1). 여기서 LLM 을 부르지 않는다.
    """
    user = _current_user(request)
    if user is None:
        raise ApiError(
            "LOGIN_REQUIRED",
            "데이터시트 읽기를 요청하려면 로그인이 필요합니다. 검사 자체는 로그인 없이도 무제한입니다.",
            401,
        )
    try:
        with store.session() as conn:
            return quota.request(conn, user.id, mpn)
    except quota.QuotaError as exc:
        status = 429 if exc.code == "QUOTA_EXHAUSTED" else 400
        raise ApiError(exc.code, exc.message, status) from exc


@app.get("/api/v1/rules")
async def get_rules() -> dict:
    return service.rules_catalog()


async def _accept(field: str, upload: UploadFile) -> bytes:
    """확장자와 크기를 먼저 보고, 통과한 것만 메모리로 읽는다."""
    declared = getattr(upload, "size", None)
    service.validate_upload(field, upload.filename, declared or 0)
    data = await upload.read()
    if declared is None:
        service.validate_upload(field, upload.filename, len(data))
    return data


@app.post("/api/v1/checks", status_code=201)
async def create_check(
    request: Request,
    netlist: UploadFile | None = File(default=None),
    bom: UploadFile | None = File(default=None),
    firmware: UploadFile | None = File(default=None),
    previous_netlist: UploadFile | None = File(default=None),
) -> JSONResponse:
    # **검사는 로그인해야 만들 수 있다** (8/24 팀장 결정 · CLAUDE.md 4절).
    #
    # 결과를 *보는* 것은 안 막는다 — 주소를 아는 사람은 그대로 열린다.
    # 그 선을 지켜야 요금표가 파는 「결과 링크 공유」가 참이 된다.
    #
    # **파일을 받기 전에 막는다.** 핸들러 안쪽에서 검사하면 멀티파트 파서가
    # 이미 파일을 다 메모리에 올린 뒤라, 막으려던 비용을 그대로 치른다.
    #
    # **8/26 — 벽을 결과 뒤로 옮겼다.** 결정 자체(검사하려면 계정이 필요하다)는
    # 그대로다. 다만 처음 온 사람은 이 도구가 무엇을 내놓는지 못 본 채로 계정을
    # 요구받고 있었다. `guest.py` 에 이유를 적어 뒀다.
    user = _current_user(request)
    guest_used = 0
    if user is None:
        # **키를 들고 왔는데 안 맞으면 게스트로 흘려보내지 않는다.**
        #
        # CI 러너가 죽은 키로 부르면 401 과 "시크릿을 확인하세요"를 받아야 한다.
        # 게스트로 통과시키면 검사는 성공하고 키가 죽은 줄 아무도 모른다 —
        # 그러다 두 번째 PR 에서 갑자기 막히고, 그때는 원인을 못 찾는다.
        if apikeys.looks_like_key(_bearer(request)):
            raise ApiError(
                "INVALID_API_KEY",
                "API 키가 맞지 않습니다. 「내 검사」 화면에서 키를 다시 만들어 주세요.",
                401,
            )
        guest_used = guest.used_count(request.cookies.get(guest.COOKIE))
        if guest_used >= guest.FREE_CHECKS:
            raise ApiError(
                "LOGIN_REQUIRED",
                "체험 검사를 다 쓰셨습니다. 계속 쓰시려면 계정을 만들어 주세요 — "
                "이메일 하나면 되고, 결과가 계정에 남습니다.",
                401,
            )

    if netlist is None or not netlist.filename:
        raise service.netlist_required()

    netlist_bytes = await _accept("netlist", netlist)

    bom_name = None
    bom_bytes = None
    if bom is not None and bom.filename:
        bom_bytes = await _accept("bom", bom)
        bom_name = bom.filename

    firmware_name = None
    firmware_bytes = None
    if firmware is not None and firmware.filename:
        firmware_bytes = await _accept("firmware", firmware)
        firmware_name = firmware.filename

    previous_name = None
    previous_bytes = None
    if previous_netlist is not None and previous_netlist.filename:
        previous_bytes = await _accept("previous_netlist", previous_netlist)
        previous_name = previous_netlist.filename

    result = service.run_check(
        netlist_bytes=netlist_bytes,
        netlist_filename=netlist.filename,
        bom_bytes=bom_bytes,
        bom_filename=bom_name,
        firmware_filename=firmware_name,
        firmware_bytes=firmware_bytes,
        previous_netlist_bytes=previous_bytes,
        previous_netlist_filename=previous_name,
        fact_store=facts,
    )
    # 로그인했으면 주인을 붙이고, 게스트면 안 붙인다.
    # **주인 없는 검사는 「내 검사」에 안 뜬다** — 그래서 화면이 가입하라고 말할 수 있다.
    store.save(result, owner_id=user.id if user else None)

    # 검사는 밀리초 단위로 끝난다. 만들자마자 done 이다.
    body = {
        "check_id": result["check_id"],
        "status": result["status"],
        # 주인이 붙었는지 화면이 알아야 "내 검사"에 뜬다는 말을 할 수 있다.
        "owned": user is not None,
    }
    # **`status_code` 를 직접 준다.** `JSONResponse` 를 돌려주면 데코레이터의
    # `status_code=201` 이 무시된다 — `_with_session` 에서 이미 한 번 겪었다.
    if user is not None:
        return JSONResponse(body, status_code=201)

    # 게스트가 한 번 썼다. **표를 갱신해서 돌려준다.**
    # 남은 횟수를 같이 실어서, 화면이 "이제 가입해야 합니다"를 지어내지 않고 말한다.
    body["guest_remaining"] = max(0, guest.FREE_CHECKS - (guest_used + 1))
    response = JSONResponse(body, status_code=201)
    response.set_cookie(
        guest.COOKIE,
        guest.issue(guest_used + 1),
        max_age=guest.TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    return response


@app.get("/api/v1/checks/{check_id}")
async def get_check(check_id: str, request: Request) -> dict:
    """결과 조회 — **주소를 아는 사람은 연다.** 로그인은 필요 없다.

    검사를 *만드는* 것은 로그인해야 하지만(8/24 결정), 결과를 *보는* 것은 안 막는다.
    그 선이 로그인 벽의 범위다 — 링크를 받은 사람까지 가입시키면
    요금표가 파는 「결과 링크 공유」가 거짓말이 되고, "링크 하나로 근거까지 보인다"는
    최대 강점이 사라진다.

    **한동안 주인 있는 검사를 주인만 열게 해 뒀다.** 그때는 로그아웃 검사가
    가능해서 "공유용"과 "내 것"이 자연히 갈렸는데, 로그인 벽이 생기면서 모든 검사에
    주인이 붙었다. 그 규칙을 그대로 두면 **아무도 공유를 못 한다.**

    **주인이 비공개로 바꾼 검사는 예외다.** 그때는 주인만 열린다.
    비공개는 유료가 아니라 **무료 기능**이다 — 보안을 요금제 뒤에 두면
    돈을 안 내는 사람의 회로도를 인질로 잡는 셈이 된다.

    없는 검사와 남의 비공개 검사를 **똑같이 404 로 돌려준다.** 403 은
    "여기 뭔가 있다"를 알려주는데, ID 를 못 맞히는 것이 접근 통제의 전부라
    존재 자체를 안 알리는 편이 맞다.
    """
    user = _current_user(request)
    owner = store.owner_of(check_id)
    mine = user is not None and owner is not None and owner == user.id

    if store.visibility_of(check_id) == "private" and not mine:
        raise ApiError("CHECK_NOT_FOUND", "그런 검사가 없습니다.", 404)

    result = store.get(check_id)
    # **저장한 payload 에 없는 두 값을 여기서 붙인다.**
    # 검사한 순간의 판정 기록과 달리 나중에 바뀌는 값이라 payload 에 섞지 않는다.
    #
    # `owned` 가 없으면 남에게도 공개 범위 버튼이 뜨고, 눌러야 404 를 만난다.
    # 보는 사람은 이미 이 검사를 열었으므로 새로 새는 정보가 없다.
    result["visibility"] = store.visibility_of(check_id) or "link"
    result["owned"] = mine
    return result


@app.post("/api/v1/checks/{check_id}/visibility")
async def set_visibility(check_id: str, request: Request) -> dict:
    """공개 범위를 바꾼다. **주인만.**

    `{"visibility": "private"}` 또는 `{"visibility": "link"}`.
    """
    user = _current_user(request)
    if user is None or store.owner_of(check_id) != user.id:
        # 주인이 아닌 사람에게 "그 검사는 당신 것이 아닙니다" 라고 알려줄 이유가 없다
        raise ApiError("CHECK_NOT_FOUND", "그런 검사가 없습니다.", 404)

    body = await request.json()
    wanted = str((body or {}).get("visibility") or "")
    try:
        store.set_visibility(check_id, wanted)
    except ValueError as exc:
        raise ApiError("BAD_VISIBILITY", str(exc), 400) from exc
    return {"check_id": check_id, "visibility": wanted}


@app.delete("/api/v1/checks/{check_id}")
async def delete_check(check_id: str, request: Request) -> dict:
    """내 검사를 내린다.

    로그인을 만들기 전에는 **올린 결과를 내릴 방법이 아예 없었다.** 재배포 때
    사라지긴 했지만 그건 정책이 아니라 사고다.

    주인 없는 검사는 여기서 지울 수 없다. 누구의 것인지 알 방법이 없어서,
    지우게 두면 남의 결과를 아무나 지운다.
    """
    user = _require_user(request)
    owner = store.owner_of(check_id)
    if owner is None or owner != user.id:
        raise service.check_not_found(check_id)
    store.delete(check_id)
    return {"deleted": check_id}
