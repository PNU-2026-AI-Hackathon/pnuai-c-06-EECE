"""데이터시트 읽기 요청 할당량.

**여기가 우리 돈이 나가는 유일한 자리다.** 판정은 순수 함수라 원가가 0이고,
검사는 무제한 무료다. 그래서 이 테스트가 지키는 것은 두 가지다 —

1. 원가가 **안** 드는 일에 할당량을 쓰지 않는가 (이미 읽은 부품)
2. 원가가 드는 일이 한도를 넘지 못하는가
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from web import quota


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT, password_hash TEXT, created_at TEXT);
        CREATE TABLE part_facts (mpn TEXT, field TEXT, value TEXT);
        """
    )
    conn.execute("INSERT INTO users VALUES ('u1', 'a@b.c', 'x', '2026-08-01')")
    conn.commit()
    quota.init(conn)
    return conn


AUG = datetime(2026, 8, 15, tzinfo=timezone.utc)
SEP = datetime(2026, 9, 1, tzinfo=timezone.utc)


# ── 원가가 안 드는 일은 세지 않는다 ────────────────────────────

def test_이미_읽은_부품은_할당량을_안_쓴다():
    """`part_facts` 는 공용이다. 두 번째 요청부터 원가가 0이라 셀 이유가 없다."""
    conn = _conn()
    conn.execute("INSERT INTO part_facts VALUES ('ESP32-C6', 'vcc', '3.3')")
    conn.commit()

    out = quota.request(conn, "u1", "esp32-c6", now=AUG)

    assert out["status"] == "known"
    assert out["quota"]["used"] == 0


def test_같은_부품을_두_번_요청해도_한_번만_센다():
    conn = _conn()
    quota.request(conn, "u1", "AAA-1", now=AUG)
    out = quota.request(conn, "u1", "aaa-1", now=AUG)

    assert out["status"] == "already_requested"
    assert quota.quota_of(conn, "u1", now=AUG).used == 1


# ── 한도 ──────────────────────────────────────────────────

def test_무료는_월_3건에서_막힌다():
    conn = _conn()
    for i in range(quota.MONTHLY_LIMIT["free"]):
        assert quota.request(conn, "u1", f"PART-{i}", now=AUG)["status"] == "queued"

    with pytest.raises(quota.QuotaError) as caught:
        quota.request(conn, "u1", "PART-X", now=AUG)
    assert caught.value.code == "QUOTA_EXHAUSTED"


def test_달이_바뀌면_저절로_열린다():
    """`month` 칼럼으로 세므로 지우는 작업이 필요 없다."""
    conn = _conn()
    for i in range(quota.MONTHLY_LIMIT["free"]):
        quota.request(conn, "u1", f"PART-{i}", now=AUG)

    assert quota.quota_of(conn, "u1", now=SEP).left == quota.MONTHLY_LIMIT["free"]
    assert quota.request(conn, "u1", "PART-NEW", now=SEP)["status"] == "queued"


def test_요금제마다_한도가_다르다():
    conn = _conn()
    conn.execute("UPDATE users SET plan = 'pro' WHERE id = 'u1'")
    conn.commit()

    assert quota.quota_of(conn, "u1", now=AUG).limit == quota.MONTHLY_LIMIT["pro"]


def test_모르는_요금제는_무료로_본다():
    """**없는 요금제에 큰 한도를 주지 않는다.** 오타나 조작이 이득이 되면 안 된다."""
    conn = _conn()
    conn.execute("UPDATE users SET plan = 'enterprise_lol' WHERE id = 'u1'")
    conn.commit()

    assert quota.quota_of(conn, "u1", now=AUG).limit == quota.MONTHLY_LIMIT["free"]


# ── 입력 ──────────────────────────────────────────────────

def test_부품번호가_아니면_거절한다():
    conn = _conn()
    for bad in ("", "  ", "a" * 100, "<script>", "부품"):
        with pytest.raises(quota.QuotaError) as caught:
            quota.request(conn, "u1", bad, now=AUG)
        assert caught.value.code == "BAD_MPN"


def test_대소문자만_다르면_같은_부품이다():
    assert quota.normalize_mpn("  esp32-c6 ") == "ESP32-C6"


# ── 운영이 볼 것 ───────────────────────────────────────────

def test_많이_요청된_부품이_먼저_나온다():
    """**사람이 이 목록을 보고 데이터시트를 읽는다.** 수요가 큰 것부터 읽어야 한다."""
    conn = _conn()
    conn.execute(
        "INSERT INTO users (id, email, password_hash, created_at) VALUES ('u2', 'x@y.z', 'x', '2026-08-01')"
    )
    conn.commit()
    quota.request(conn, "u1", "POPULAR", now=AUG)
    quota.request(conn, "u2", "POPULAR", now=AUG)
    quota.request(conn, "u1", "RARE", now=AUG)

    rows = quota.pending(conn)
    assert rows[0]["mpn"] == "POPULAR" and rows[0]["requests"] == 2


def test_part_facts_표가_없어도_요청은_된다():
    """사실 DB 를 안 심은 배포에서도 서비스는 살아 있어야 한다."""
    conn = sqlite3.connect(":memory:")
    conn.executescript("CREATE TABLE users (id TEXT PRIMARY KEY, plan TEXT);")
    conn.execute("INSERT INTO users VALUES ('u1', 'free')")
    conn.commit()
    quota.init(conn)

    assert quota.request(conn, "u1", "ANY-1", now=AUG)["status"] == "queued"
