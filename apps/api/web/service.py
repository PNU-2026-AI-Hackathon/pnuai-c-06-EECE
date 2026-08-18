"""HTTP 프레임워크를 모르는 서비스 층.

여기에 검증·저장·응답 조립이 전부 들어 있다. app.py 는 얇은 어댑터일 뿐이다.
덕분에 FastAPI 없이도 이 층 전체를 테스트할 수 있다.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from prefab.firmware import load_zip
from prefab.netlist.d356 import NetlistParseError
from prefab.report import build_result, build_rules_catalog
from prefab.runner import analyze

# --------------------------------------------------------------------- 상수

#: 파일 하나당 상한
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

ALLOWED_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "netlist": (".d356", ".ipc", ".txt"),
    "bom": (".csv",),
    "firmware": (".zip",),
}

#: 오류 메시지는 사용자에게 그대로 보인다. 필드 이름도 한국어로 부른다.
FIELD_LABELS = {"netlist": "넷리스트", "bom": "BOM", "firmware": "펌웨어 zip"}

CHECK_ID_PREFIX = "chk_"
CHECK_ID_BYTES = 3  # → 16진수 6자리


# --------------------------------------------------------------------- 오류

@dataclass(frozen=True)
class ApiError(Exception):
    """계약의 오류 응답 그대로. message 는 사용자에게 그대로 노출된다.

    무엇이 잘못됐고 어떻게 고치는지 알려준다. 사과하지 않는다.
    """

    code: str
    message: str
    status: int

    def to_dict(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message}}


def netlist_required() -> ApiError:
    return ApiError("NETLIST_REQUIRED", "넷리스트 파일이 필요합니다.", 422)


def netlist_parse_failed(detail: str) -> ApiError:
    return ApiError("NETLIST_PARSE_FAILED", detail, 422)


def file_too_large(field: str) -> ApiError:
    mb = MAX_UPLOAD_BYTES // (1024 * 1024)
    label = FIELD_LABELS.get(field, field)
    return ApiError("FILE_TOO_LARGE", f"{label} 파일이 {mb}MB를 넘습니다. 줄여서 다시 올려 주세요.", 413)


def unsupported_file_type(field: str) -> ApiError:
    allowed = " / ".join(ALLOWED_EXTENSIONS[field])
    label = FIELD_LABELS.get(field, field)
    return ApiError(
        "UNSUPPORTED_FILE_TYPE",
        f"{label} 는 {allowed} 확장자만 받습니다.",
        415,
    )


def check_not_found(check_id: str) -> ApiError:
    return ApiError("CHECK_NOT_FOUND", f"검사 {check_id} 를 찾지 못했습니다. 주소를 확인해 주세요.", 404)


def internal_error() -> ApiError:
    return ApiError(
        "INTERNAL_ERROR",
        "검사 도중 서버에서 처리하지 못한 오류가 발생했습니다. 파일을 바꿔 다시 시도해 주세요.",
        500,
    )


# --------------------------------------------------------------------- 검증

def validate_upload(field: str, filename: str | None, size: int) -> None:
    if not filename:
        raise netlist_required() if field == "netlist" else unsupported_file_type(field)
    if size > MAX_UPLOAD_BYTES:
        raise file_too_large(field)
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS[field]:
        raise unsupported_file_type(field)


# --------------------------------------------------------------------- 실행

def new_check_id() -> str:
    return CHECK_ID_PREFIX + secrets.token_hex(CHECK_ID_BYTES)


def utc_now() -> str:
    """계약 예시와 같은 UTC 문자열. 시간대는 서버가 정하지 않는다."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def firmware_unreadable() -> ApiError:
    return ApiError(
        "FIRMWARE_UNREADABLE",
        "펌웨어 zip 을 열지 못했습니다. 소스 파일(.ino / .cpp / .h)이 들어 있는 zip 인지 확인해 주세요.",
        422,
    )


def run_check(
    *,
    netlist_bytes: bytes,
    netlist_filename: str,
    bom_filename: str | None = None,
    firmware_filename: str | None = None,
    firmware_bytes: bytes | None = None,
    check_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """업로드된 입력으로 검사를 끝내고 계약 응답을 만든다.

    지금 규모(네트 8 · 부품 10 · 소스 1개 · 규칙 4개)에서는 밀리초 단위로 끝난다.
    큐를 쓰지 않는다. 5초를 넘기기 시작하면 그때 BackgroundTasks 로 바꾼다.
    """
    sources: "dict[str, str] | None" = None
    if firmware_bytes:
        try:
            sources = load_zip(firmware_bytes)
        except zipfile.BadZipFile as exc:
            raise firmware_unreadable() from exc
        if not sources:
            raise firmware_unreadable()

    text = netlist_bytes.decode("utf-8", errors="replace")
    try:
        analysis = analyze(
            text,
            filename=netlist_filename,
            bom=bom_filename,
            firmware_sources=sources,
        )
    except NetlistParseError as exc:
        raise netlist_parse_failed(str(exc)) from exc

    return build_result(
        check_id=check_id or new_check_id(),
        created_at=created_at or utc_now(),
        analysis=analysis,
        netlist_filename=netlist_filename,
        bom_filename=bom_filename,
        firmware_filename=firmware_filename,
    )


def rules_catalog() -> dict[str, Any]:
    return build_rules_catalog()


# --------------------------------------------------------------------- 저장

class Store:
    """SQLite 한 개. Postgres 를 쓰지 않는다 (CLAUDE.md 9절)."""

    def __init__(self, path: "str | Path" = "prefab.db") -> None:
        self.path = str(path)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _session(self) -> "Iterator[sqlite3.Connection]":
        """트랜잭션을 닫고 **연결도 닫는다.**

        `with sqlite3.connect(...) as conn:` 은 커밋만 하고 연결을 닫지 않는다.
        그대로 두면 요청마다 연결이 새는데, 리눅스에서는 티가 안 나고
        윈도우에서는 파일 핸들이 잡혀서 DB 파일을 지울 수 없게 된다.
        """
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init(self) -> None:
        with self._session() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checks (
                    id         TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    payload    TEXT NOT NULL
                )
                """
            )

    def save(self, result: dict[str, Any]) -> None:
        with self._session() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO checks (id, created_at, payload) VALUES (?, ?, ?)",
                (result["check_id"], result["created_at"], json.dumps(result, ensure_ascii=False)),
            )

    def get(self, check_id: str) -> dict[str, Any]:
        with self._session() as conn:
            row = conn.execute("SELECT payload FROM checks WHERE id = ?", (check_id,)).fetchone()
        if row is None:
            raise check_not_found(check_id)
        return json.loads(row["payload"])

    def purge_older_than(self, cutoff_iso: str) -> int:
        """오래된 검사를 지운다. 업로드 파일은 애초에 디스크에 남기지 않는다."""
        with self._session() as conn:
            cur = conn.execute("DELETE FROM checks WHERE created_at < ?", (cutoff_iso,))
            return cur.rowcount
