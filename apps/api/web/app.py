"""FastAPI 어댑터.

이 파일에는 판정도 검증 규칙도 없다. 전부 service.py 에 있다.
여기가 하는 일은 HTTP ↔ dict 변환뿐이다.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.formparsers import MultiPartParser

from prefab.datasheet.store import FactStore

from . import service, usage
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
#: **여기서 CORS 는 보안 경계가 아니다.** 이 API 는 인증이 없어서 `curl` 로는
#: 어차피 누구나 부른다. CORS 가 막는 것은 *브라우저*뿐이고, 브라우저는 페이지가
#: `Origin` 을 `localhost` 로 위조하게 두지 않는다. 개발 포트를 더 여는 것으로
#: 늘어나는 위험이 없다 (헌법 2-3 — 조용한 실패가 더 비싸다).
ALLOWED_ORIGINS = DEV_ORIGINS + [
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
    if request.method != "POST" or not request.url.path.startswith("/api/v1/checks"):
        return await call_next(request)

    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > service.MAX_UPLOAD_BYTES:
        err = service.body_too_large()
        return JSONResponse(status_code=err.status, content=err.to_dict())

    if not RATE_LIMIT_ENABLED:
        return await call_next(request)

    key = client_key(request.headers.get("x-forwarded-for"), _peer(request))
    decision = limiter.check(key)
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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,
)

store = service.Store(DB_PATH)

#: 업로드 없이 볼 수 있는 실측 보드 결과 하나 (F-4).
#: 넣지 못하면 None 이 되고, 루트 응답에서도 빠진다 — 있는 척하지 않는다.
SAMPLE_CHECK_ID = service.seed_sample(store)
#: 부품 사실 DB. **checks 와 같은 파일**을 쓴다 — SQLite 한 개 (CLAUDE.md 9절).
facts = FactStore(DB_PATH)

#: 커밋된 사실 파일을 기동 때 심는다. 배포 이미지에는 DB 가 없기 때문이다 —
#: 안 심으면 데이터시트 해제가 배포된 서버에서만 조용히 사라진다.
#: 이 덕분에 **영구 디스크가 필요 없다.** 못 심으면 빈 목록이고, 루트 응답에 그대로 실린다.
SEEDED_PARTS = service.seed_facts(os.getenv("PREFAB_PARTS", "parts"), facts)


# --------------------------------------------------------------------- 오류

@app.exception_handler(ApiError)
async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content=exc.to_dict())


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
    netlist: UploadFile | None = File(default=None),
    bom: UploadFile | None = File(default=None),
    firmware: UploadFile | None = File(default=None),
    previous_netlist: UploadFile | None = File(default=None),
) -> dict:
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
    store.save(result)

    # 검사는 밀리초 단위로 끝난다. 만들자마자 done 이다.
    return {"check_id": result["check_id"], "status": result["status"]}


@app.get("/api/v1/checks/{check_id}")
async def get_check(check_id: str) -> dict:
    return store.get(check_id)
