"""샘플 검사 (F-4) — 업로드 없이 결과부터 보여주는 경로.

이 파일이 지키는 것은 하나다: **싣고 다니는 JSON 이 엔진보다 낡지 않는 것.**

배포 이미지에 `tests/` 가 없어서(`.dockerignore`) 서버가 켜질 때 픽스처를 다시
돌릴 수 없다. 그래서 미리 뽑아 둔 결과를 패키지에 싣는데, 그러면 엔진을 고칠 때마다
이 파일이 조용히 낡는다. 여기서 매번 다시 뽑아 대조해서 그 조용함을 없앤다.
"""

from __future__ import annotations

import json
from pathlib import Path

from prefab.datasheet.seed import seed_facts
from prefab.datasheet.store import FactStore
from prefab.firmware import load_directory
from prefab.report import build_result
from prefab.runner import analyze
from prefab.samples import SAMPLE_CHECK_ID, SAMPLE_PATH, load_sample

FIXTURES = Path(__file__).parent / "fixtures"
NETLIST = FIXTURES / "esp32-c6-presence-smart-light.d356"
BOM = FIXTURES / "esp32-c6-presence-smart-light.bom.csv"
FIRMWARE = FIXTURES / "esp32-c6-presence-smart-light.firmware"


PARTS = Path(__file__).parent.parent / "parts"


def _seeded_store(tmp_path) -> FactStore:
    """커밋된 `parts/*.json` 만으로 만든 사실 DB. **서버가 기동 때 하는 것과 같다.**

    한동안 샘플을 사실 없이 뽑았다. 이유는 "로컬 DB 상태가 섞이면 커밋된 파일만으로
    재현할 수 없다" 였고, 그때는 맞는 말이었다. **지금은 사실이 커밋돼 있다** —
    입력이 `parts/*.json` 뿐이고 정렬된 순서로 읽으므로 결과가 결정적이다.

    낡은 근거를 그대로 두었더니 **업로드 없이 보는 첫 화면에서만 해제가 0건**이었다.
    같은 보드를 직접 올리면 2건이 해제되는데도 그랬다.
    """
    store = FactStore(tmp_path / "sample-facts.db")
    seed_facts(PARTS, store)
    return store


def _regenerate(tmp_path) -> dict:
    """샘플을 만든 것과 **똑같은** 입력으로 다시 뽑는다."""
    a = analyze(
        NETLIST.read_text(encoding="utf-8", errors="replace"),
        filename=NETLIST.name,
        bom_bytes=BOM.read_bytes(),
        firmware_sources=load_directory(FIRMWARE),
        fact_store=_seeded_store(tmp_path),
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


def test_실려_있는_샘플이_지금_엔진과_같다(tmp_path):
    """어긋나면 다시 뽑아야 한다 — 명령은 `src/prefab/samples/__init__.py` 에 있다."""
    assert load_sample() == _regenerate(tmp_path), (
        "샘플이 엔진보다 낡았습니다. 두 줄로 다시 뽑으세요 —\n"
        "  PREFAB_DB=/tmp/sample-facts.db python -m prefab --facts-load parts/*.json\n"
        "  PREFAB_DB=/tmp/sample-facts.db python -m prefab tests/fixtures/esp32-c6-presence-smart-light.d356 --bom tests/fixtures/esp32-c6-presence-smart-light.bom.csv --firmware tests/fixtures/esp32-c6-presence-smart-light.firmware --json > src/prefab/samples/check.sample.json\n"
        "**사실 DB 를 먼저 심는 것이 핵심입니다.** 서버가 기동할 때 하는 것과 같습니다. "
        "빈 DB 로 뽑으면 해제가 0건이 되어, 업로드 없이 보는 첫 화면에서만 차별점이 사라집니다."
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


def test_샘플이_데이터시트_해제를_보여준다():
    """**업로드 없이 보는 첫 화면이다.** 여기서 해제가 0건이면 차별점이 안 보인다.

    한 번 그랬다 — 샘플만 사실 없이 뽑혀서, 같은 보드를 직접 올리면 2건이 해제되는데
    샘플에서는 0건이었다. 그 조용한 어긋남을 여기서 막는다.
    """
    s = load_sample()
    assert s["summary"]["cleared"] > 0, (
        "샘플에 해제된 판정이 없습니다. 사실 DB 를 심지 않고 뽑았을 때 이렇게 됩니다 — "
        "`src/prefab/samples/__init__.py` 의 명령을 확인하세요."
    )


def test_해제된_판정에는_데이터시트_근거가_붙어_있다():
    """해제는 **출처가 붙어야만** 성립한다. 근거 없이 지우면 그냥 놓친 것이다."""
    s = load_sample()
    cleared = [f for f in s["findings"] if f["verdict"] == "PASS"]
    assert cleared, "해제된 판정이 없습니다"
    for f in cleared:
        kinds = {e["kind"] for e in f["evidence"]}
        assert "datasheet" in kinds, f"{f['rule']}: 근거 종류 {kinds}"


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
