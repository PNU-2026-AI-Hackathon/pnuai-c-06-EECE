"""원가·사용량 집계.

여기서 지키는 것은 숫자 자체가 아니라 **숫자가 DB 에서 나온다는 것**이다.
손으로 적은 숫자는 반드시 낡는다.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3

import pytest

from web import usage


def _db(tmp_path, *, parts=(), checks=()):
    tmp_path = pathlib.Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = str(tmp_path / "u.db")
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE part_facts (mpn TEXT, field TEXT, created_at TEXT,"
        " confidence TEXT, source_tier TEXT, PRIMARY KEY (mpn, field))"
    )
    conn.execute("CREATE TABLE checks (id TEXT PRIMARY KEY, created_at TEXT, payload TEXT)")
    for mpn, field in parts:
        conn.execute(
            "INSERT INTO part_facts VALUES (?,?,'2026-08-23','HIGH','official')", (mpn, field)
        )
    for i, cleared in enumerate(checks):
        conn.execute(
            "INSERT INTO checks VALUES (?,'2026-08-23',?)",
            (f"chk_{i}", json.dumps({"summary": {"cleared": cleared}})),
        )
    conn.commit()
    conn.close()
    return path


def test_부품은_중복을_세지_않는다(tmp_path):
    """부품 하나에 사실이 여럿이다. **LLM 호출은 부품당 한 번**이므로 부품을 센다."""
    path = _db(tmp_path, parts=[("TP4056", "voh_max"), ("TP4056", "vcc"), ("ESP32", "voh_max")])
    got = usage.collect(path)
    assert got.parts == 2
    assert got.facts == 3


def test_DB_를_만든_LLM_호출_수는_부품_수와_같다(tmp_path):
    """갈라지면 원가 모델이 틀렸다는 뜻이다 — 그래서 따로 들고 비교한다."""
    path = _db(tmp_path, parts=[("A", "x"), ("B", "y")])
    got = usage.collect(path)
    assert got.llm_calls_building_db == got.parts


def test_사실이_덜어낸_오탐을_누계로_센다(tmp_path):
    path = _db(tmp_path, parts=[("A", "x")], checks=[3, 0, 5])
    assert usage.collect(path).cleared_by_facts == 8


def test_검사를_아무리_많이_해도_검사가_부르는_LLM_은_0_이다(tmp_path):
    """**이게 사업 모델이다.** 비율이 아니라 0 이다.

    비율로 적었더니 갓 배포한 서버에서 1 보다 작게 나왔다 — 숫자는 맞지만
    읽는 사람에게는 원가가 안 빠진다는 뜻으로 보인다. 실제로는 정반대다.
    """
    few = usage.collect(_db(tmp_path / "a", parts=[("A", "x")], checks=[0]))
    (tmp_path / "b").mkdir(parents=True, exist_ok=True)
    many = usage.collect(_db(tmp_path / "b", parts=[("A", "x")], checks=[0] * 5000))
    assert few.llm_calls_serving_checks == 0
    assert many.llm_calls_serving_checks == 0


def test_표가_아직_없어도_0_을_돌려준다(tmp_path):
    """기동 직후엔 표가 없다. **없는 표를 예외로 만들면 화면이 같이 죽는다.**"""
    path = str(tmp_path / "empty.db")
    sqlite3.connect(path).close()
    got = usage.collect(path)
    assert (got.parts, got.facts, got.checks, got.cleared_by_facts) == (0, 0, 0, 0)


def test_읽지_못한_결과_하나가_전체_합계를_망치지_않는다(tmp_path):
    path = _db(tmp_path, parts=[("A", "x")], checks=[2, 4])
    conn = sqlite3.connect(path)
    conn.execute("INSERT INTO checks VALUES ('chk_bad','2026-08-23','{깨진 JSON')")
    conn.commit()
    conn.close()
    assert usage.collect(path).cleared_by_facts == 6


def test_사전으로_바꾸면_0_도_함께_실린다(tmp_path):
    path = _db(tmp_path, parts=[("A", "x")], checks=[1] * 4)
    out = usage.collect(path).to_dict()
    assert out["llm_calls_serving_checks"] == 0
    assert set(out) >= {
        "parts", "facts", "checks", "cleared_by_facts", "llm_calls_building_db",
    }


# ── HTTP ────────────────────────────────────────────────────────────

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from conftest import sign_in  # noqa: E402


def test_엔드포인트가_실측을_그대로_내려준다(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFAB_DB", str(tmp_path / "api.db"))
    # **쿠키가 `Secure` 면 TestClient(http)가 버린다.** 그러면 로그인이 조용히
    # 안 되고, 검사가 401 로 막힌다 — 로그인 벽이 생기면서 실제로 그랬다.
    monkeypatch.setenv("COOKIE_SECURE", "0")
    import importlib

    from web import app as app_module

    importlib.reload(app_module)
    client = TestClient(app_module.app)
    sign_in(client)  # 검사를 만들려면 로그인해야 한다 (8/24)

    body = client.get("/api/v1/usage").json()
    # 기동 때 커밋된 사실 파일을 심으므로 부품이 0 이 아니어야 한다.
    assert body["parts"] > 0
    assert body["llm_calls_building_db"] == body["parts"]
    assert body["llm_calls_serving_checks"] == 0

    before = body["checks"]
    client.post(
        "/api/v1/checks",
        files={"netlist": ("b.net.xml", open("board/board.net.xml", "rb").read())},
    )
    assert client.get("/api/v1/usage").json()["checks"] == before + 1
