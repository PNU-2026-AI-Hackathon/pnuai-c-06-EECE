"""서비스 층 — 업로드 검증 · 오류 코드 · 저장소.

FastAPI 없이 도는 테스트다. HTTP 어댑터가 바뀌어도 이 계약은 그대로여야 한다.
"""

from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

import pytest

from web import service

FIXTURE = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"
FIRMWARE_DIR = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.firmware"


def _firmware_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path in sorted(FIRMWARE_DIR.iterdir()):
            zf.writestr(path.name, path.read_text(encoding="utf-8"))
    return buf.getvalue()


def _raises(fn) -> service.ApiError:
    try:
        fn()
    except service.ApiError as exc:
        return exc
    raise AssertionError("ApiError 가 나와야 한다")


def test_netlist_extensions_accepted():
    for name in ("board.d356", "board.ipc", "board.txt", "BOARD.D356"):
        service.validate_upload("netlist", name, 100)


def test_wrong_extension_is_415_with_a_usable_message():
    err = _raises(lambda: service.validate_upload("netlist", "board.pdf", 100))
    assert (err.code, err.status) == ("UNSUPPORTED_FILE_TYPE", 415)
    assert ".d356" in err.message


def test_oversize_file_is_413():
    err = _raises(
        lambda: service.validate_upload("netlist", "board.d356", service.MAX_UPLOAD_BYTES + 1)
    )
    assert (err.code, err.status) == ("FILE_TOO_LARGE", 413)
    assert "10MB" in err.message


def test_missing_netlist_is_422():
    err = _raises(lambda: service.validate_upload("netlist", None, 0))
    assert (err.code, err.status) == ("NETLIST_REQUIRED", 422)


def test_bom_only_accepts_csv():
    service.validate_upload("bom", "parts.csv", 10)
    assert _raises(lambda: service.validate_upload("bom", "parts.xlsx", 10)).status == 415


def test_firmware_only_accepts_zip():
    service.validate_upload("firmware", "src.zip", 10)
    assert _raises(lambda: service.validate_upload("firmware", "main.cpp", 10)).status == 415


def test_garbage_netlist_is_422_parse_failed():
    err = _raises(
        lambda: service.run_check(
            netlist_bytes="넷리스트가 아닙니다".encode(), netlist_filename="x.d356"
        )
    )
    assert (err.code, err.status) == ("NETLIST_PARSE_FAILED", 422)


def test_run_check_on_the_real_board():
    result = service.run_check(
        netlist_bytes=FIXTURE.read_bytes(), netlist_filename=FIXTURE.name
    )
    assert result["status"] == "done"
    assert result["check_id"].startswith("chk_")
    assert len(result["findings"]) == 2
    assert result["summary"]["rules_run"] == 2


def test_created_at_is_utc_with_a_trailing_z():
    """1-3 답변: 서버는 UTC 로 준다. 시간대 변환은 화면이 한다."""
    assert service.utc_now().endswith("Z")
    assert len(service.utc_now()) == len("2026-08-18T11:20:00Z")


def test_firmware_zip_runs_the_differentiating_rules():
    """펌웨어를 받으면 R07 · R08 이 실제로 돈다."""
    result = service.run_check(
        netlist_bytes=FIXTURE.read_bytes(),
        netlist_filename=FIXTURE.name,
        firmware_filename="src.zip",
        firmware_bytes=_firmware_zip(),
    )
    assert result["summary"]["rules_run"] == 6
    assert (result["summary"]["critical"], result["summary"]["warning"]) == (4, 1)
    assert result["pipeline"][2]["status"] == "done"
    assert result["inputs"]["firmware"]["filename"] == "src.zip"
    assert result["inputs"]["firmware"]["files"] == 1


def test_firmware_absent_is_reported_not_hidden():
    result = service.run_check(netlist_bytes=FIXTURE.read_bytes(), netlist_filename=FIXTURE.name)
    assert result["pipeline"][2] == {
        "step": 3, "name": "펌웨어 정적 분석", "status": "skipped", "detail": "펌웨어 미제출",
    }
    assert result["inputs"]["firmware"] is None


def test_zip_without_sources_is_422():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "소스가 아니다")
    err = _raises(
        lambda: service.run_check(
            netlist_bytes=FIXTURE.read_bytes(),
            netlist_filename=FIXTURE.name,
            firmware_filename="src.zip",
            firmware_bytes=buf.getvalue(),
        )
    )
    assert (err.code, err.status) == ("FIRMWARE_UNREADABLE", 422)


def test_broken_zip_is_422_not_a_crash():
    err = _raises(
        lambda: service.run_check(
            netlist_bytes=FIXTURE.read_bytes(),
            netlist_filename=FIXTURE.name,
            firmware_filename="src.zip",
            firmware_bytes=b"PK\x03\x04 not really a zip",
        )
    )
    assert err.code == "FIRMWARE_UNREADABLE"


def test_store_round_trip_and_404():
    with tempfile.TemporaryDirectory() as tmp:
        store = service.Store(Path(tmp) / "t.db")
        result = service.run_check(
            netlist_bytes=FIXTURE.read_bytes(), netlist_filename=FIXTURE.name
        )
        store.save(result)
        assert store.get(result["check_id"]) == result

        err = _raises(lambda: store.get("chk_nope"))
        assert (err.code, err.status) == ("CHECK_NOT_FOUND", 404)


def test_store_does_not_hold_the_db_file_open():
    """연결이 새면 윈도우에서 DB 파일을 못 지운다. 리눅스에서는 티가 안 난다.

    sqlite3 의 `with conn:` 은 커밋만 하고 연결을 닫지 않는다. 한 번 물렸던 함정이다.
    """
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "leak.db"
        store = service.Store(db)
        result = service.run_check(
            netlist_bytes=FIXTURE.read_bytes(), netlist_filename=FIXTURE.name
        )
        store.save(result)
        store.get(result["check_id"])
        store.purge_older_than("1970-01-01T00:00:00Z")

        db.unlink()  # 핸들이 남아 있으면 윈도우에서 PermissionError 가 난다
        assert not db.exists()


def test_check_ids_do_not_collide():
    ids = {service.new_check_id() for _ in range(500)}
    assert len(ids) > 480  # 16진수 6자리. 시연 규모에서 충돌하지 않는다


def test_error_payload_shape_matches_the_contract():
    payload = service.netlist_required().to_dict()
    assert set(payload) == {"error"}
    assert set(payload["error"]) == {"code", "message"}
