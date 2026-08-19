"""검증 측정 (E-3).

숫자를 내는 코드라서 **숫자가 거짓말하지 않는 것**이 전부다.
읽지 못한 케이스를 조용히 빼거나, 잴 수 없는 것을 0으로 적으면 안 된다.
"""

from __future__ import annotations

import json

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
