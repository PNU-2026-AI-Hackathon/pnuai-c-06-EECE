"""검증 측정 (E-3).

숫자를 내는 코드라서 **숫자가 거짓말하지 않는 것**이 전부다.
읽지 못한 케이스를 조용히 빼거나, 잴 수 없는 것을 0으로 적으면 안 된다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prefab.measure import CaseResult, Report, format_report, run

FOLDER = "tests/fixtures/injected"


@pytest.fixture
def report():
    return run(FOLDER)


# ── 실제 데이터셋 ───────────────────────────────────────────────────


def test_라벨된_케이스가_전부_돈다(report):
    assert report.errors == [], "읽지 못한 케이스가 있으면 숫자가 불완전하다"
    assert len(report.cases) >= 7


def test_결함을_넣은_케이스는_잡아야_한다(report):
    for c in report.cases:
        assert not c.missed, f"{c.id}: {c.missed} 를 놓쳤다"


def test_결함이_없는_케이스에서_경고가_뜨면_오탐이다(report):
    for c in report.clean_cases:
        assert not c.spurious, f"{c.id}: {c.spurious} 가 잘못 떴다"


def test_실측_보드가_데이터셋에_들어_있다(report):
    """합성만으로 재면 '우리가 만든 상황에서만 맞다'를 못 벗어난다."""
    kinds = {c.kind for c in report.cases}
    assert "실측" in kinds


def test_음성_케이스가_있어야_오탐율을_잴_수_있다(report):
    assert len(report.clean_cases) >= 3


# ── 셈이 정직한가 ───────────────────────────────────────────────────


def test_기대한_것이_없으면_검출율은_잴_수_없음이다():
    """0% 가 아니다. 잴 수 없는 것을 0 으로 적으면 숫자가 거짓말한다."""
    r = Report(cases=[CaseResult("a", "음성", [], [])])
    assert r.recall is None
    assert "잴 수 없음" in format_report(r)


def test_음성_케이스가_없으면_오탐율도_잴_수_없음이다():
    r = Report(cases=[CaseResult("a", "양성", ["R12"], ["R12"])])
    assert r.false_positive_rate is None


def test_미검출과_오탐을_따로_센다():
    c = CaseResult("a", "양성", ["R11", "R12"], ["R12", "R04"])
    assert c.missed == ["R11"] and c.spurious == ["R04"] and not c.ok


def test_해제된_발견은_경고로_세지_않는다(report):
    """PASS 는 '데이터시트로 확인했다'는 뜻이지 경고가 아니다."""
    r04 = next(c for c in report.cases if c.id == "r04-within-limit")
    assert r04.fired == []


def test_읽지_못한_케이스를_숨기지_않는다(tmp_path):
    """조용히 빼면 숫자가 좋아 보인다 (CLAUDE.md 2-4)."""
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"cases": [
        {"id": "없는파일", "expect": [], "netlist": "없다.d356"},
    ]}), encoding="utf-8")
    r = run(tmp_path)
    assert len(r.errors) == 1
    assert "숫자에서 빠져 있습니다" in format_report(r)


def test_한계를_보고서에_같이_적는다(report):
    """숫자만 떼어 인용되면 안 된다."""
    text = format_report(report)
    assert "이 숫자가 못 재는 것" in text
    assert "재현율" in text and "E-1" in text


# ── CLI ─────────────────────────────────────────────────────────────


def test_CLI로_돌릴_수_있다(capsys):
    from prefab.__main__ import main

    assert main(["--measure", FOLDER]) == 0
    assert "검출" in capsys.readouterr().out


def test_읽지_못한_케이스가_있으면_0이_아닌_코드로_끝난다(tmp_path, capsys):
    from prefab.__main__ import main

    (tmp_path / "MANIFEST.json").write_text(json.dumps({"cases": [
        {"id": "x", "expect": [], "netlist": "없다.d356"},
    ]}), encoding="utf-8")
    assert main(["--measure", str(tmp_path)]) == 1


# ── 측정에서 빠진 규칙이 없는가 ─────────────────────────────────────
#
# **이게 없어서 두 규칙이 조용히 빠져 있었다.** R10 은 `measure` 가 이전 넷리스트를
# 안 넘겨서 아예 안 돌았고, R11 은 dedupe 로 R12 가 되는 케이스뿐이라 한 번도
# 안 세어졌다. 그런데 보고서는 "검출 17/17 (100%)" 이라고 적고 있었다 —
# **12개 규칙 중 10개만 잰 숫자였다.**


def test_모든_규칙에_양성_케이스가_있다():
    """규칙을 새로 만들면 케이스도 같이 만들어야 한다. 안 그러면 안 재진다.

    100% 라는 숫자가 '전부 잡았다'가 아니라 '잰 것만 잡았다'가 되는 것을 막는다.
    """
    from prefab import catalog

    manifest = json.loads(
        (Path(FOLDER) / "MANIFEST.json").read_text(encoding="utf-8")
    )["cases"]
    covered = {rule for case in manifest for rule in case.get("expect", [])}
    missing = [s.id for s in catalog.CATALOG if s.id not in covered]
    assert not missing, (
        f"양성 케이스가 없는 규칙: {missing}. "
        "scripts/make_injected.py 에 양성·음성 짝을 추가하세요 — "
        "케이스가 없으면 그 규칙은 검출율에 안 들어갑니다."
    )


def test_이전_넷리스트가_필요한_케이스를_실제로_넘긴다(report):
    """`before` 를 안 넘기면 R10 은 아무 말도 안 하고 조용히 미검출이 된다."""
    drift = next(c for c in report.cases if c.id == "r10-pin-moved")
    assert "R10" in drift.fired, "이전 넷리스트가 규칙까지 안 갔다"
    assert not drift.missed
