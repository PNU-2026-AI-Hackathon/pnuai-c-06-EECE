"""샘플 검사 (F-4) — 업로드 없이 결과부터 보여주는 경로.

이 파일이 지키는 것은 하나다: **싣고 다니는 JSON 이 엔진보다 낡지 않는 것.**

배포 이미지에 `tests/` 가 없어서(`.dockerignore`) 서버가 켜질 때 픽스처를 다시
돌릴 수 없다. 그래서 미리 뽑아 둔 결과를 패키지에 싣는데, 그러면 엔진을 고칠 때마다
이 파일이 조용히 낡는다. 여기서 매번 다시 뽑아 대조해서 그 조용함을 없앤다.
"""

from __future__ import annotations

import json
from pathlib import Path

from prefab.firmware import load_directory
from prefab.report import build_result
from prefab.runner import analyze
from prefab.samples import SAMPLE_CHECK_ID, SAMPLE_PATH, load_sample

FIXTURES = Path(__file__).parent / "fixtures"
NETLIST = FIXTURES / "esp32-c6-presence-smart-light.d356"
BOM = FIXTURES / "esp32-c6-presence-smart-light.bom.csv"
FIRMWARE = FIXTURES / "esp32-c6-presence-smart-light.firmware"


def _regenerate() -> dict:
    """샘플을 만든 것과 **똑같은** 입력으로 다시 뽑는다.

    부품 사실 DB 는 일부러 안 쓴다 — 로컬 DB 상태에 따라 결과가 달라지면
    커밋된 파일만으로 재현할 수 없게 된다.
    """
    a = analyze(
        NETLIST.read_text(encoding="utf-8", errors="replace"),
        filename=NETLIST.name,
        bom_bytes=BOM.read_bytes(),
        firmware_sources=load_directory(FIRMWARE),
    )
    sample = load_sample()
    return build_result(
        check_id=sample["check_id"],
        created_at=sample["created_at"],
        analysis=a,
        netlist_filename=NETLIST.name,
        bom_filename=BOM.name,
        firmware_filename=FIRMWARE.name,
    )


# ── 낡지 않는가 ─────────────────────────────────────────────────────


def test_실려_있는_샘플이_지금_엔진과_같다():
    """어긋나면 다시 뽑아야 한다 — 명령은 `src/prefab/samples/__init__.py` 에 있다."""
    assert load_sample() == _regenerate(), (
        "샘플이 엔진보다 낡았습니다. "
        "python -m prefab tests/fixtures/esp32-c6-presence-smart-light.d356 "
        "--bom ... --firmware ... --json > src/prefab/samples/check.sample.json"
    )


def test_샘플이_패키지_안에_있다():
    """배포 이미지에 tests/ 가 없다. 패키지 밖을 가리키면 서버에서 못 읽는다."""
    assert SAMPLE_PATH.exists()
    assert SAMPLE_PATH.parent.name == "samples"
    assert "tests" not in SAMPLE_PATH.parts


# ── 계약을 안 깨는가 ────────────────────────────────────────────────


def test_샘플이_계약_모양_그대로다():
    s = load_sample()
    assert s["check_id"] == SAMPLE_CHECK_ID
    assert s["status"] == "done"
    for key in ("inputs", "summary", "pipeline", "findings", "netlist"):
        assert key in s, key
    total = s["summary"]["rules_run"] + s["summary"]["rules_skipped"]
    assert total == s["summary"]["rules_total"]


def test_샘플이_실제로_보여줄_게_있다():
    """빈 결과를 띄우면 데모에서 아무 말도 못 한다."""
    s = load_sample()
    rules = {f["rule"] for f in s["findings"]}
    # 차별 규칙이 화면에 보이는 것이 이 데모의 요점이다
    assert {"R07", "R08"} <= rules, rules
    assert s["summary"]["critical"] > 0
    assert s["inputs"]["firmware"] is not None
    assert s["inputs"]["bom"] is not None


# ── 저장소에 들어가는가 ─────────────────────────────────────────────


def test_서버가_켜질_때_샘플이_조회_가능해진다(tmp_path):
    """새 엔드포인트를 만들지 않는다. 기존 조회 경로로 그대로 나온다."""
    from web import service

    store = service.Store(tmp_path / "t.db")
    assert service.seed_sample(store) == SAMPLE_CHECK_ID
    got = store.get(SAMPLE_CHECK_ID)
    assert got == load_sample()


def test_두_번_넣어도_괜찮다(tmp_path):
    from web import service

    store = service.Store(tmp_path / "t.db")
    service.seed_sample(store)
    service.seed_sample(store)
    assert store.get(SAMPLE_CHECK_ID)["check_id"] == SAMPLE_CHECK_ID


def test_샘플을_못_읽어도_서버는_뜬다(tmp_path, monkeypatch):
    """샘플은 있으면 좋은 것이지 서버가 뜨는 조건이 아니다."""
    from prefab import samples
    from web import service

    monkeypatch.setattr(samples, "SAMPLE_PATH", tmp_path / "없다.json")
    monkeypatch.setattr(service, "load_sample", samples.load_sample)
    store = service.Store(tmp_path / "t.db")
    assert service.seed_sample(store) is None


def test_깨진_샘플도_예외를_안_던진다(tmp_path, monkeypatch):
    from prefab import samples

    broken = tmp_path / "broken.json"
    broken.write_text("{ 이건 JSON 이 아니다", encoding="utf-8")
    monkeypatch.setattr(samples, "SAMPLE_PATH", broken)
    assert samples.load_sample() is None
