"""FastAPI 어댑터.

이 파일에는 판정도 검증 규칙도 없다. 전부 service.py 에 있다.
여기가 하는 일은 HTTP ↔ dict 변환뿐이다.
"""

from __future__ import annotations

import os
import warnings

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.formparsers import MultiPartParser

from prefab.datasheet.store import FactStore

from . import service, storage, usage, waitlist
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

#: 커밋된 사실 파일을 기동 때 심는다. 배포 이미지에는 DB 가 없기 때문이다 —
#: 안 심으면 데이터시트 해제가 배포된 서버에서만 조용히 사라진다.
#: 이 덕분에 **영구 디스크가 필요 없다.** 못 심으면 빈 목록이고, 루트 응답에 그대로 실린다.
SEEDED_PARTS = service.seed_facts(os.getenv("PREFAB_PARTS", "parts"), facts)


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
    return out


# ------------------------------------------------------------------- 인증

def _current_user(request: Request):
    """세션 쿠키로 사용자를 찾는다. 없으면 `None`.

    **없다고 거절하지 않는다.** 로그아웃 상태에서도 검사가 되고 결과가 열려야
    하기 때문이다 (헌법 4절 단서 1). 거절이 필요한 자리에서만 따로 거절한다.
    """
    return accounts.user_for_token(request.cookies.get(SESSION_COOKIE))


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
) -> dict:
    # **검사는 로그인해야 만들 수 있다** (8/24 팀장 결정 · CLAUDE.md 4절).
    #
    # 결과를 *보는* 것은 안 막는다 — 주소를 아는 사람은 그대로 열린다.
    # 그 선을 지켜야 요금표가 파는 「결과 링크 공유」가 참이 된다.
    #
    # **파일을 받기 전에 막는다.** 핸들러 안쪽에서 검사하면 멀티파트 파서가
    # 이미 파일을 다 메모리에 올린 뒤라, 막으려던 비용을 그대로 치른다.
    user = _current_user(request)
    if user is None:
        raise ApiError(
            "LOGIN_REQUIRED",
            "검사를 실행하려면 로그인이 필요합니다. 계정은 이메일 하나면 만들 수 있습니다.",
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
    # 로그인했으면 주인을 붙이고, 아니면 안 붙인다. **로그인을 요구하지 않는다** —
    # 로그아웃 상태에서도 검사가 되어야 한다 (헌법 4절 단서 1).
    store.save(result, owner_id=user.id)

    # 검사는 밀리초 단위로 끝난다. 만들자마자 done 이다.
    return {
        "check_id": result["check_id"],
        "status": result["status"],
        # 주인이 붙었는지 화면이 알아야 "내 검사"에 뜬다는 말을 할 수 있다.
        "owned": user is not None,
    }


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

    비공개 링크는 요금표의 **Pro 항목**이다. 지금은 만들지 않았으므로
    "없는 것을 있는 척" 하지 않는다 — 무료에서는 주소가 곧 접근 권한이고,
    그 사실을 `/privacy` 가 그대로 적는다 (헌법 2-2 · 2-4).

    접근 통제는 **ID 를 못 맞히는 것**이 전부다. 그래서 16바이트(32자리)를 쓴다.
    """
    return store.get(check_id)


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
