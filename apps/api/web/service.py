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

from prefab.bom import BomParseError
from prefab.firmware import load_zip
from prefab.netlist.d356 import NetlistParseError
from prefab.netlist.detect import parse_any
from prefab.report import build_result, build_rules_catalog
from prefab.datasheet.seed import seed_facts as _seed_facts
from prefab.datasheet.store import FactStore
from prefab.runner import analyze
from prefab.samples import SAMPLE_CHECK_ID, load_sample

from . import waitlist
from . import apikeys
from . import quota

# --------------------------------------------------------------------- 상수

#: 파일 하나당 상한
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

ALLOWED_EXTENSIONS: dict[str, tuple[str, ...]] = {
    # `.xml`·`.net` 은 KiCad 회로도 넷리스트(kicadxml)다. 형식은 확장자가 아니라
    # **내용으로** 가른다 (`netlist.detect`) — 여기 목록은 실수로 엉뚱한 파일을
    # 올리는 것을 막는 1차 방어일 뿐이다.
    "netlist": (".d356", ".ipc", ".txt", ".xml", ".net"),
    # 이전 회로도도 넷리스트다. **형식이 같을 필요는 없다** — 예전에는 IPC-D-356 으로
    # 뽑았고 지금은 회로도 넷리스트로 뽑는 경우가 실제로 생긴다.
    "previous_netlist": (".d356", ".ipc", ".txt", ".xml", ".net"),
    "bom": (".csv",),
    "firmware": (".zip",),
}

#: 오류 메시지는 사용자에게 그대로 보인다. 필드 이름도 한국어로 부른다.
FIELD_LABELS = {
    "netlist": "넷리스트",
    "previous_netlist": "이전 회로도",
    "bom": "BOM",
    "firmware": "펌웨어 zip",
}

CHECK_ID_PREFIX = "chk_"

#: 검사 ID 의 무작위 바이트 수. **이 값이 접근 통제의 전부다.**
#:
#: `GET /api/v1/checks/{id}` 에는 인증이 없다. 그리고 검사 결과에는 사용자의
#: **실제 소스 코드 줄과 회로도 전체**(네트·부품 목록)가 들어 있다 — 남의 지적재산이다.
#: 그러니 ID 를 못 맞히는 것이 유일한 방어선이고, 그 방어선은 길이가 정한다.
#:
#: 3바이트로 뒀었다. 16진수 6자리 = 1,670만 조합이고 **초당 100회면 47시간에
#: 전수 조사가 끝난다.** 무료 플랜이라 요청 제한도 없다. 실서비스로는 못 나갈 값이었다.
#:
#: 16바이트면 2^128 이라 맞힐 수 없다. 계약은 형식을 강제하지 않는다 —
#: 예시가 `chk_7f3a2b` 였을 뿐이고, 프론트는 `check_id` 를 그대로 들고 다닌다.
CHECK_ID_BYTES = 16  # → 16진수 32자리


# --------------------------------------------------------------------- 오류

@dataclass(eq=False)
class ApiError(Exception):
    """계약의 오류 응답 그대로. message 는 사용자에게 그대로 노출된다.

    무엇이 잘못됐고 어떻게 고치는지 알려준다. 사과하지 않는다.

    **`frozen=True` 가 아니다.** 한동안 그랬는데, 예외를 얼리면 파이썬이
    `__traceback__` 을 못 붙인다. 평범한 `raise` 는 통과하지만
    **`with` 블록 안에서 던지면 터진다** — `contextlib` 이 `gen.throw()` 로
    예외를 넘기면서 traceback 을 쓰기 때문이다.

        with store.session() as conn:
            raise ApiError(...)      # FrozenInstanceError: __traceback__

    증상이 고약하다. 실패가 `ApiError` 가 아니라 `FrozenInstanceError` 로
    나와서 500 이 되고, 화면은 우리가 쓴 문구 대신 서버 오류를 본다.

    `eq=False` 로 두는 이유는 해시 가능성을 지키기 위해서다 — 예외는 값이
    아니라 사건이라 동일성 비교가 맞다.
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


def previous_netlist_parse_failed(filename: str, detail: str) -> ApiError:
    """이전 회로도만 못 읽었을 때. **지금 회로도 오류와 구분해서 말한다.**

    둘 다 넷리스트라 오류 문구가 똑같이 생겼다. 어느 파일을 고쳐야 하는지
    말해 주지 않으면 사용자는 멀쩡한 파일을 뜯어본다.
    """
    return ApiError(
        "PREVIOUS_NETLIST_PARSE_FAILED",
        f"이전 회로도({filename})를 읽지 못했습니다 — {detail} "
        "이 파일을 빼고 다시 올리면 지금 회로도만으로 검사합니다.",
        422,
    )


def bom_parse_failed(detail: str) -> ApiError:
    return ApiError("BOM_PARSE_FAILED", detail, 422)


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


def too_many_requests(window: str, retry_after: int) -> ApiError:
    """한도 초과. **막힌 이유와 언제 다시 되는지를 같이 말한다.**

    "요청이 너무 많습니다"만 돌려주면 받는 쪽은 자기가 무엇을 잘못했는지도,
    기다리면 풀리는 건지도 모른다. 그러면 새로고침을 연타하게 되고, 그건
    한도를 만든 이유를 정확히 거스른다.
    """
    return ApiError(
        "RATE_LIMITED",
        f"같은 주소에서 짧은 시간에 너무 많이 올렸습니다({window} 한도). "
        f"{retry_after}초 뒤에 다시 시도해 주세요.",
        429,
    )


def body_too_large() -> ApiError:
    """본문 전체가 상한을 넘음 — **파일을 읽기 전에** 끊을 때 쓴다.

    `file_too_large` 와 달리 어느 칸이 컸는지 모른다. 아직 안 읽었기 때문이다.
    """
    mb = MAX_UPLOAD_BYTES // (1024 * 1024)
    return ApiError(
        "FILE_TOO_LARGE",
        f"올린 파일이 {mb}MB를 넘습니다. 줄여서 다시 올려 주세요.",
        413,
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
    bom_bytes: bytes | None = None,
    bom_filename: str | None = None,
    firmware_filename: str | None = None,
    firmware_bytes: bytes | None = None,
    previous_netlist_bytes: bytes | None = None,
    previous_netlist_filename: str | None = None,
    check_id: str | None = None,
    created_at: str | None = None,
    fact_store: "FactStore | None" = None,
) -> dict[str, Any]:
    """업로드된 입력으로 검사를 끝내고 계약 응답을 만든다.

    지금 규모(네트 8 · 부품 10 · 소스 1개 · 규칙 4개)에서는 밀리초 단위로 끝난다.
    큐를 쓰지 않는다. 5초를 넘기기 시작하면 그때 BackgroundTasks 로 바꾼다.

    `fact_store` 를 주면 BOM 의 부품번호로 사실 DB 를 조회해 규칙에 넘긴다.
    없으면 데이터시트 축 없이 넷리스트만으로 돈다 — 지금까지와 똑같이 동작한다.
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

    # **이전 회로도는 선택이다.** 안 주면 R10 이 조용하고, 리포트가 그 사실을 적는다.
    #
    # 다만 **주고서 실패하는 것과 안 주는 것은 다르다.** 깨진 파일을 조용히 버리면
    # 사용자는 드리프트를 검사한 줄 알고 "변화 없음" 을 읽는다. 그게 이 제품에서
    # 제일 나쁜 거짓말이라 여기서 세운다 (헌법 2-4).
    #
    # 어느 쪽이 깨졌는지도 말해 준다 — `analyze` 는 둘 다 파싱해서 오류만으로는
    # 사용자가 어느 파일을 고쳐야 할지 모른다.
    previous_text: str | None = None
    if previous_netlist_bytes:
        previous_text = previous_netlist_bytes.decode("utf-8", errors="replace")
        try:
            parse_any(previous_text)
        except NetlistParseError as exc:
            raise previous_netlist_parse_failed(
                previous_netlist_filename or "이전 회로도", str(exc)
            ) from exc

    try:
        analysis = analyze(
            text,
            filename=netlist_filename,
            bom_bytes=bom_bytes,
            firmware_sources=sources,
            fact_store=fact_store,
            previous_netlist_text=previous_text,
        )
    except NetlistParseError as exc:
        raise netlist_parse_failed(str(exc)) from exc
    except BomParseError as exc:
        raise bom_parse_failed(str(exc)) from exc

    return build_result(
        check_id=check_id or new_check_id(),
        created_at=created_at or utc_now(),
        analysis=analysis,
        netlist_filename=netlist_filename,
        bom_filename=bom_filename,
        firmware_filename=firmware_filename,
        bom=analysis.bom,
    )


def rules_catalog() -> dict[str, Any]:
    return build_rules_catalog()


def seed_facts(facts_dir: "Path | str", store) -> list[str]:
    """커밋된 부품 사실 파일을 DB 에 심는다. 넣은 부품번호 목록을 돌려준다.

    **구현은 `prefab.datasheet.seed` 에 있다.** 웹만 필요한 일이 아니라서다 —
    샘플 검사를 다시 뽑을 때도 같은 사실이 들어가야 한다. 한쪽에만 두었다가
    샘플이 사실 없이 뽑히는 일이 실제로 있었다.
    """
    return _seed_facts(facts_dir, store)


def seed_sample(store: "Store") -> str | None:
    """샘플 검사를 저장소에 넣는다 (F-4). 넣은 ID 또는 None.

    데모에서 **업로드 없이 결과 화면부터** 띄우기 위한 것이다.
    `GET /api/v1/checks/chk_sample01` 로 조회된다 — 새 엔드포인트가 아니다.

    **실패해도 조용히 넘어간다.** 샘플이 없다고 서버가 안 뜨면 그게 훨씬 나쁘다.
    대신 넣었는지 아닌지를 돌려주므로, 부른 쪽이 그 사실을 노출할 수 있다.
    """
    sample = load_sample()
    if sample is None:
        return None
    try:
        store.save(sample)
    except Exception:  # noqa: BLE001 - 샘플 때문에 서버가 죽으면 안 된다
        return None
    return sample.get("check_id", SAMPLE_CHECK_ID)


# --------------------------------------------------------------------- 저장

def _netlist_name(body: dict[str, Any]) -> str | None:
    netlist = (body.get("inputs") or {}).get("netlist")
    if isinstance(netlist, dict):
        return netlist.get("filename")
    return netlist if isinstance(netlist, str) else None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


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

    @contextmanager
    def session(self) -> "Iterator[sqlite3.Connection]":
        """같은 DB 파일을 쓰는 다른 표(대기 명단 등)를 위한 공개 통로.

        **연결을 새로 만들지 않는다.** 이 클래스가 이미 여는 방식(트랜잭션 · 닫기)을
        그대로 쓰게 해서, 파일 핸들이 새는 자리를 하나로 유지한다.
        """
        with self._session() as conn:
            yield conn

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
            # 로그인 없이 만든 검사는 주인이 없다 (`NULL`). **그게 정상이다** —
            # 로그아웃 상태에서도 검사가 되어야 하기 때문이다 (헌법 4절).
            #
            # `ALTER TABLE` 로 붙이는 이유: 이미 검사가 들어 있는 DB 가 돌아가고
            # 있다. 표를 새로 만들면 그 결과들이 사라진다.
            if "owner_id" not in _columns(conn, "checks"):
                conn.execute("ALTER TABLE checks ADD COLUMN owner_id TEXT")
            # 공개 범위. **기본은 `link`** — 지금까지 만든 검사가 전부 그렇게
            # 동작해 왔고, 기본을 `private` 로 두면 남에게 보낸 링크가 조용히 죽는다.
            if "visibility" not in _columns(conn, "checks"):
                conn.execute(
                    "ALTER TABLE checks ADD COLUMN visibility TEXT NOT NULL DEFAULT 'link'"
                )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS checks_owner ON checks (owner_id, created_at)"
            )
            # 대기 명단은 같은 DB 파일 안에 둔다 (헌법 9절 — SQLite 하나)
            waitlist.init(conn)
            quota.init(conn)
            apikeys.init(conn)

    def save(self, result: dict[str, Any], owner_id: str | None = None) -> None:
        with self._session() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO checks (id, created_at, payload, owner_id)"
                " VALUES (?, ?, ?, ?)",
                (
                    result["check_id"],
                    result["created_at"],
                    json.dumps(result, ensure_ascii=False),
                    owner_id,
                ),
            )

    def delete(self, check_id: str) -> None:
        with self._session() as conn:
            conn.execute("DELETE FROM checks WHERE id = ?", (check_id,))

    #: 공개 범위. 값은 이 둘뿐이다.
    #:
    #: `link`     주소를 아는 사람은 누구나 (무료 플랜의 공유 방식)
    #: `private`  주인만. 남이 주소를 알아도 404
    #:
    #: **404 로 돌려준다. 403 이 아니다.** 403 은 "여기 뭔가 있다"를 알려주는데,
    #: 검사 ID 는 못 맞히는 것이 접근 통제의 전부라 존재 자체를 안 알리는 편이 맞다.
    VISIBILITIES = ("link", "private")

    def visibility_of(self, check_id: str) -> str | None:
        """이 검사의 공개 범위. 검사가 없으면 `None`."""
        with self._session() as conn:
            row = conn.execute(
                "SELECT visibility FROM checks WHERE id = ?", (check_id,)
            ).fetchone()
        return (row["visibility"] or "link") if row else None

    def set_visibility(self, check_id: str, visibility: str) -> None:
        if visibility not in self.VISIBILITIES:
            raise ValueError(f"알 수 없는 공개 범위입니다: {visibility}")
        with self._session() as conn:
            conn.execute(
                "UPDATE checks SET visibility = ? WHERE id = ?", (visibility, check_id)
            )

    def owner_of(self, check_id: str) -> str | None:
        """이 검사의 주인. 없으면 `None` (로그인 없이 만든 검사)."""
        with self._session() as conn:
            row = conn.execute(
                "SELECT owner_id FROM checks WHERE id = ?", (check_id,)
            ).fetchone()
        return row["owner_id"] if row else None

    def list_for_owner(self, owner_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """한 사람의 검사 목록. 최신순.

        **본문(payload)을 통째로 싣지 않는다.** 목록 한 번에 검사 50건의 전체
        결과를 내려보내면 수 MB 가 된다. 요약만 꺼낸다.
        """
        with self._session() as conn:
            rows = conn.execute(
                "SELECT id, created_at, payload FROM checks WHERE owner_id = ?"
                " ORDER BY created_at DESC LIMIT ?",
                (owner_id, limit),
            ).fetchall()

        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                body = json.loads(row["payload"])
            except json.JSONDecodeError:
                # 읽지 못한 결과 하나 때문에 목록 전체를 포기하지 않는다.
                continue
            out.append(
                {
                    "check_id": row["id"],
                    "created_at": row["created_at"],
                    "summary": body.get("summary", {}),
                    # `inputs.netlist` 는 문자열이 아니라 {filename, nets, parts} 다.
                    # 그대로 실었더니 목록에 사전이 통째로 나갔다.
                    "netlist_filename": _netlist_name(body),
                }
            )
        return out

    def get(self, check_id: str) -> dict[str, Any]:
        """저장한 것을 **그대로** 돌려준다.

        공개 범위(`visibility`)와 주인 여부(`owned`)는 여기서 안 섞는다.
        payload 는 검사한 순간의 판정 기록이고 그 둘은 나중에 바뀌는 값이라,
        저장소의 왕복이 손실 없다는 성질을 지키는 편이 낫다.
        응답에 싣는 것은 API 층(`web/app.py`)이 한다.
        """
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
