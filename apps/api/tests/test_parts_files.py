"""리포에 커밋된 부품 사실 파일 (`parts/*.json`).

DB 파일(`prefab.db`)은 `.gitignore` 에 있다. **커밋되는 진실은 이 JSON 들뿐이고**,
누가 받아서 `--facts-load` 하면 같은 결과가 나와야 한다.
그걸 보장하는 게 이 파일이다. 값이 상해도 아무도 모르는 상태를 만들지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prefab.datasheet.facts import VOH_MAX
from prefab.datasheet.store import FactStore
from prefab.runner import analyze
from prefab.types import Verdict

PARTS = Path("parts")
FIXTURES = Path("tests/fixtures")

#: 서식은 부품이 아니다. `mpn` 이 비어 있어 일부러 거절되게 돼 있다.
TEMPLATE = PARTS / "_TEMPLATE.json"


def part_files() -> list[Path]:
    return sorted(p for p in PARTS.glob("*.json") if p != TEMPLATE)


def test_커밋된_부품_파일이_하나는_있다():
    """0개면 데이터시트 축이 화면에서 한 번도 안 나타난다."""
    assert part_files(), "parts/*.json 이 없다"


@pytest.mark.parametrize("path", part_files(), ids=lambda p: p.stem)
def test_거절되는_사실_없이_전부_저장된다(path, tmp_path):
    """출처 없는 값이나 이유 없는 '모름'이 섞여 들어가지 않았는지 본다."""
    store = FactStore(tmp_path / "t.db")
    report = store.save_json(path.read_text(encoding="utf-8"))
    assert report.ok, [f"{r.field}: {r.why}" for r in report.rejected]
    assert report.stored + report.negative > 0


@pytest.mark.parametrize("path", part_files(), ids=lambda p: p.stem)
def test_출처가_공식이고_주소가_있다(path):
    """어디서 받은 PDF 인지 모르면 다음 사람이 검증할 수 없다."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw.get("source_url", "").startswith("http")
    assert raw.get("source_tier") in ("official", "distributor", "unofficial")


@pytest.mark.parametrize("path", part_files(), ids=lambda p: p.stem)
def test_파일명이_부품번호와_맞는다(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert path.stem == raw["mpn"].lower(), "파일명과 mpn 이 어긋나면 찾을 수 없다"


def test_서식은_통째로_거절된다(tmp_path):
    """실수로 서식을 넣어도 DB 가 더러워지지 않아야 한다."""
    store = FactStore(tmp_path / "t.db")
    assert not store.save_json(TEMPLATE.read_text(encoding="utf-8")).ok
    assert store.size() == (0, 0)


# ── 실제로 경고가 지워지는가 ────────────────────────────────────────


def _real_board(store: FactStore | None):
    return analyze(
        (FIXTURES / "esp32-c6-presence-smart-light.d356").read_text(),
        filename="esp32-c6-presence-smart-light.d356",
        bom_bytes=(FIXTURES / "esp32-c6-presence-smart-light.bom.csv").read_bytes(),
        fact_store=store,
    )


def _loaded_store(tmp_path) -> FactStore:
    store = FactStore(tmp_path / "t.db")
    for path in part_files():
        store.save_json(path.read_text(encoding="utf-8"))
    return store


def test_커밋된_파일만으로_PRESENCE_3V3_두_건이_해제된다(tmp_path):
    """이게 제품이 파는 장면이다 — 측정 없이 문서로 해제.

    U2 는 5V 로 도는데 출력은 3.3V 다. 넷리스트만 보면 위험해 보이고,
    데이터시트를 읽으면 아니다. 그 차이가 여기서 화면에 나타난다.
    """
    before = _real_board(None).engine.findings
    after = _real_board(_loaded_store(tmp_path)).engine.findings

    assert not [f for f in before if f.verdict is Verdict.PASS], "넣기 전에 이미 해제돼 있다"

    cleared = [f for f in after if f.verdict is Verdict.PASS]
    # R11 은 dedup 으로 R12 에 합쳐진다. 남는 해제는 하나다.
    assert {(f.rule, f.net) for f in cleared} == {("R12", "PRESENCE_3V3")}
    assert "R11" in cleared[0].suggestion, "합쳐진 규칙을 조용히 버리지 않는다"
    assert len(after) == len(before), "해제는 발견을 지우는 게 아니라 판정을 바꾸는 것이다"


def test_해제된_발견에는_데이터시트_출처가_붙는다(tmp_path):
    """근거 없는 해제는 사용자가 믿을 수 없다 (CLAUDE.md 2-1)."""
    for f in _real_board(_loaded_store(tmp_path)).engine.findings:
        if f.verdict is not Verdict.PASS:
            continue
        cites = [e for e in f.evidence if e.kind == "datasheet"]
        assert len(cites) == 1, f"{f.rule} 해제에 출처가 없다"
        assert cites[0].page and cites[0].quote and cites[0].table
        assert f.unresolved_reason is None


def test_K1은_여전히_미결로_남는다(tmp_path):
    """부품 하나를 읽었다고 다 풀린 척하지 않는다.

    K1 은 도메인을 추론으로만 알아서 구동하는 쪽인지도 모른다.
    하드웨어 측정(8/25 모듈 도착) 또는 `input_pullup_to` 를 기다리는 건이다.
    """
    found = [
        f
        for f in _real_board(_loaded_store(tmp_path)).engine.findings
        if f.net == "_IN_ACTIVE_LOW" and f.rule == "R12"
    ]
    assert len(found) == 1
    assert found[0].verdict is not Verdict.PASS
    assert "핀 방향과 내부 풀업" in found[0].unresolved_reason


def test_사실이_들어가면_4단계가_미구현이라고_말하지_않는다(tmp_path):
    """한 일을 안 했다고 적지 않는다 (CLAUDE.md 2-4)."""
    from prefab.report import build_result

    r = build_result(
        check_id="chk_t", created_at="2026-08-19T00:00:00Z",
        analysis=_real_board(_loaded_store(tmp_path)),
        netlist_filename="b.d356", bom_filename="b.csv",
    )
    step4, step5 = r["pipeline"][3], r["pipeline"][4]
    assert "미구현" not in step4["detail"]
    # 몇 개를 모았고 무엇이 남았는지 둘 다 말해야 한다. 숫자는 parts/ 가 늘면 바뀐다.
    assert "개 수집" in step4["detail"]
    assert "미수집: JQC-3FF-S-Z" in step4["detail"], "릴레이는 아직 데이터시트가 없다"
    assert step5["status"] == "done" and "판정 1건에 근거로 사용" in step5["detail"]
