"""FastAPI 어댑터.

이 파일에는 판정도 검증 규칙도 없다. 전부 service.py 에 있다.
여기가 하는 일은 HTTP ↔ dict 변환뿐이다.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from prefab.datasheet.store import FactStore

from . import service
from .service import ApiError

# --------------------------------------------------------------------- 설정

#: 배포 시 ALLOWED_ORIGINS 환경변수로 Vercel URL 을 넣는다. 쉼표로 여러 개.
DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"

ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",") if o.strip()
]

#: Vercel 프리뷰 배포는 URL 이 매번 바뀐다. 정규식으로 함께 허용한다.
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX", r"https://.*\.vercel\.app")

DB_PATH = os.getenv("PREFAB_DB", "prefab.db")

app = FastAPI(title="Prefab API", version="0.1.0", docs_url="/docs")

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
#: 부품 사실 DB. **checks 와 같은 파일**을 쓴다 — SQLite 한 개 (CLAUDE.md 9절).
facts = FactStore(DB_PATH)


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
async def root() -> dict[str, str]:
    return {"service": "prefab-api", "docs": "/docs", "contract": "/api/v1/rules"}


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
    if firmware is not None and firmware.filename:
        await _accept("firmware", firmware)
        firmware_name = firmware.filename

    result = service.run_check(
        netlist_bytes=netlist_bytes,
        netlist_filename=netlist.filename,
        bom_bytes=bom_bytes,
        bom_filename=bom_name,
        firmware_filename=firmware_name,
        fact_store=facts,
    )
    store.save(result)

    # 검사는 밀리초 단위로 끝난다. 만들자마자 done 이다.
    return {"check_id": result["check_id"], "status": result["status"]}


@app.get("/api/v1/checks/{check_id}")
async def get_check(check_id: str) -> dict:
    return store.get(check_id)
