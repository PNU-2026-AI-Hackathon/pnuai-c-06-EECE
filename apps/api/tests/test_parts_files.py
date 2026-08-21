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
    """실측(`measured`)도 출처다. 쪽 번호 대신 측정 기록이 그 자리를 채운다."""
    """어디서 받은 PDF 인지 모르면 다음 사람이 검증할 수 없다."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw.get("source_url", "").startswith("http")
    assert raw.get("source_tier") in ("official", "distributor", "unofficial", "measured")


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
    # R11 은 dedup 으로 R12 에 합쳐진다.
    #
    # **`_IN_ACTIVE_LOW` 는 한때 여기 같이 있었다.** 저항 실측(`input_pullup_to: none`)
    # 으로 해제됐었는데, 8/21 에 그 보드가 실제로 고장 나면서 사실이 하나 더 들어왔고
    # (`io_level: 5V`) 그 네트는 **해제에서 R04 치명으로 돌아섰다.**
    # 아래 `test_K1_은_해제됐다가_되돌아왔다` 가 그 이야기를 붙잡는다.
    assert {(f.rule, f.net) for f in cleared} == {("R12", "PRESENCE_3V3")}
    presence = next(f for f in cleared if f.net == "PRESENCE_3V3")
    assert "R11" in presence.suggestion, "합쳐진 규칙을 조용히 버리지 않는다"


def test_해제된_발견에는_데이터시트_출처가_붙는다(tmp_path):
    """근거 없는 해제는 사용자가 믿을 수 없다 (CLAUDE.md 2-1)."""
    for f in _real_board(_loaded_store(tmp_path)).engine.findings:
        if f.verdict is not Verdict.PASS:
            continue
        cites = [e for e in f.evidence if e.kind == "datasheet"]
        assert len(cites) == 1, f"{f.rule} 해제에 출처가 없다"
        # 실측 근거에는 쪽 번호가 없다. 없는 번호를 지어내는 대신 비운다.
        assert cites[0].quote and cites[0].table
        assert f.unresolved_reason is None


def test_K1_은_해제됐다가_되돌아왔다(tmp_path):
    """**이 프로젝트에서 제일 값진 한 건이다. 순서를 그대로 남긴다.**

    1. R12 가 `_IN_ACTIVE_LOW` 를 짚었다 — 5V 릴레이가 3.3V MCU 와 같은 네트다
    2. 하드웨어 담당이 모듈을 뽑아 IN↔VCC 를 20kΩ · 2MΩ 로 쟀고 둘 다 OL 이었다.
       `input_pullup_to: none` 으로 저장했고 **경고가 해제됐다**
    3. 그때 그 사실 파일에 이렇게 적어 뒀다 —
       *"저항계는 트랜지스터·다이오드 경로를 못 보므로 '저항성 풀업이 없다' 까지가
       이 측정이 말하는 전부다."*
    4. **8/21, 보드가 그 자리에서 고장 났다.** "LED가 ON은 되는데 OFF가 안된다."
       3.3V 가 K1 의 입력 문턱에 못 미쳤다
    5. `io_level: 5V` 를 실측으로 넣었고, 그 네트는 **해제에서 R04 치명으로 돌아섰다**

    적어둔 한계가 그대로 왔다. **해제를 되돌릴 수 있어야 한다** — 사실이 늘면
    판정이 바뀌는 것이 이 구조의 요점이고, 한 번 지운 것을 영영 못 되살리면
    그건 파이프라인이 아니라 예외 목록이다.
    """
    findings = [
        f for f in _real_board(_loaded_store(tmp_path)).engine.findings
        if f.net == "_IN_ACTIVE_LOW"
    ]
    assert len(findings) == 1, [(f.rule, f.verdict) for f in findings]
    f = findings[0]

    assert f.rule == "R04", f.rule
    assert f.verdict is Verdict.FAIL
    # 양쪽 데이터시트 값으로 말한다 — 추정이 아니다
    assert "5V" in f.claim and "3.6V" in f.claim, f.claim

    cite = next(e for e in f.evidence if e.kind == "datasheet")
    assert cite.quote

    # 되돌린 근거가 실측이라는 것이 화면에 남아야 한다
    assert "실측" in f.suggestion, f.suggestion


def test_저항_측정_자체는_그대로_살아_있다(tmp_path):
    """되돌아섰다고 앞의 측정을 지우지 않는다. **틀린 값이 아니라 좁은 값이었다.**

    IN↔VCC 에 저항성 풀업이 없다는 것은 지금도 사실이다. 다만 그것만으로는
    "5V 가 올라올 길이 없다" 가 안 나온다는 것을 알게 됐을 뿐이다.
    """
    facts = _loaded_store(tmp_path).lookup(["JQC-3FF-S-Z"]).facts
    pullup = facts.get("JQC-3FF-S-Z", "input_pullup_to")
    level = facts.get("JQC-3FF-S-Z", "io_level")
    assert pullup is not None and pullup.value == "none"
    assert level is not None and level.value == 5.0


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
    # 릴레이는 데이터시트가 아니라 실측으로 채웠다. 셋 다 손에 있다.
    assert "미수집" not in step4["detail"], step4["detail"]
    # 몇 건인지는 사실이 늘면 바뀐다. 개수를 여기 박지 않는다
    assert step5["status"] == "done"
    assert "판정" in step5["detail"] and "근거로 사용" in step5["detail"]


# ── 글롭으로 넣어도 죽지 않는다 ──────────────────────────────────────


def test_서식_파일은_건너뛴다(tmp_path, capsys):
    """`parts/*.json` 으로 글롭하면 `_TEMPLATE.json` 이 딸려 온다.

    그걸 거절로 세면 종료 코드가 1 이 되고 `bash -e` 로 도는 CI 스텝이 통째로 죽는다.
    **실제로 드리프트 워크플로가 그렇게 죽었다.** 심는 쪽은 원래 `_` 를 건너뛰고
    있었는데 CLI 만 그 규약을 안 따랐다.
    """
    from prefab.__main__ import _facts_load

    folder = Path(__file__).parent.parent / "parts"
    paths = sorted(str(p) for p in folder.glob("*.json"))
    assert any(Path(p).stem.startswith("_") for p in paths), "서식 파일이 없으면 이 검사가 무의미하다"

    code = _facts_load(paths, str(tmp_path / "facts.db"))
    assert code == 0, capsys.readouterr().out
    assert "서식 파일이라 건너뜁니다" in capsys.readouterr().out


# ── TP4056 — 데이터시트 한 장이 오탐 2건을 지웠다 ────────────────────


def test_TP4056_은_오픈드레인이_상수로_저장돼_있다():
    """데이터시트는 문장으로 적고 규칙은 상수를 본다. 그 사이가 비면 조용히 실패한다.

    `Open Drain Charge Status Output ... otherwise pin is in high impedance state`
    → `open-drain` 으로 옮겨져 있어야 한다.
    """
    import json

    d = json.loads((PARTS / "tp4056.json").read_text(encoding="utf-8"))
    fields = {f["field"]: f for f in d["facts"]}
    assert fields["output_type"]["value"] == "open-drain"
    assert fields["output_type"]["confidence"] == "high"
    # 원문이 남아 있어야 사용자가 "무엇을 근거로" 를 물을 때 답할 수 있다
    assert "Open Drain" in fields["output_type"]["quote"]
    assert fields["output_type"]["page"] == 2


def test_TP4056_별칭이_선언돼_있다():
    """BOM 은 `TP4056-42-ESOP8` 로 부른다. **접두어로 자동 매칭하지 않는다.**

    `ESP32-C6`(칩)과 `ESP32-C6-WROOM-1`(모듈)처럼 접두어가 같아도 다른 문서인
    경우가 있어서, 같다는 판단은 사람이 적는다.
    """
    import json

    d = json.loads((PARTS / "tp4056.json").read_text(encoding="utf-8"))
    assert "TP4056-42-ESOP8" in d["applies_to_boards"]
