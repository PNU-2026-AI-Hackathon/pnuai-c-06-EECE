"""실제 보드 골든 테스트.

이 테스트가 깨지면 되돌린다. 예외 없다 (CLAUDE.md 10절).
숫자는 전부 팀원 실물 보드(esp32-c6-presence-smart-light)를 돌려서 나온 값이다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prefab import catalog
from prefab.netlist.d356 import parse
from prefab.netlist.graph import Graph
from prefab.report import build_result
from prefab.runner import analyze
from prefab.types import Severity

FIXTURE = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"


def _analysis():
    return analyze(FIXTURE.read_text(encoding="utf-8", errors="replace"), filename=FIXTURE.name)


def test_exactly_three_findings():
    findings = _analysis().engine.findings
    assert [(f.rule, f.net) for f in findings] == [
        ("R12", "PRESENCE_3V3"),
        ("R12", "_IN_ACTIVE_LOW"),
        ("R11", "PRESENCE_3V3"),
    ]


def test_severities():
    findings = _analysis().engine.findings
    assert [f.severity for f in findings] == [
        Severity.CRITICAL,
        Severity.CRITICAL,
        Severity.WARNING,
    ]


def test_parts_and_nets():
    nl = parse(FIXTURE)
    assert (nl.part_count, nl.net_count) == (10, 8)


def test_k1_pads_split_by_x_coordinate():
    assert len(Graph(parse(FIXTURE)).clusters("K1")) == 2


def test_rules_run_plus_skipped_always_equals_the_catalog():
    engine = _analysis().engine
    assert len(engine.ran) == 2
    assert len(engine.ran) + len(engine.skipped) == catalog.TOTAL


def test_no_rule_is_silently_passed():
    """못 돌린 규칙은 전부 사유가 붙어 있어야 한다."""
    for skipped in _analysis().engine.skipped:
        assert skipped.detail


def test_result_matches_the_api_contract_shape():
    a = _analysis()
    result = build_result(
        check_id="chk_test01",
        created_at="2026-08-18T11:20:00Z",
        netlist=a.netlist,
        engine=a.engine,
        netlist_filename=FIXTURE.name,
    )
    assert set(result) == {
        "check_id",
        "status",
        "created_at",
        "inputs",
        "summary",
        "pipeline",
        "findings",
        "netlist",
    }
    assert result["summary"]["critical"] == 2
    assert result["summary"]["warning"] == 1
    assert result["summary"]["rules_run"] == 2
    assert result["summary"]["rules_total"] == catalog.TOTAL
    assert result["summary"]["parts_identified"] == 0
    assert result["summary"]["parts_total"] == 10
    assert [s["step"] for s in result["pipeline"]] == [1, 2, 3, 4, 5, 6, 7]
    assert result["pipeline"][2]["status"] == "skipped"  # 펌웨어 미제출을 숨기지 않는다
    # JSON 으로 왕복해도 깨지지 않아야 프론트가 그대로 쓴다
    assert json.loads(json.dumps(result, ensure_ascii=False)) == result


def test_evidence_has_no_empty_placeholders():
    """값이 없으면 null. 빈 문자열이나 'N/A' 로 채우지 않는다 (계약)."""
    for f in _analysis().engine.findings:
        for ev in f.evidence:
            d = ev.to_dict()
            assert "" not in d.values()
            assert "N/A" not in d.values()


@pytest.mark.xfail(
    reason="알려진 문제 #1 — R11 과 R12 가 같은 네트에 중복으로 뜬다. dedup 미구현.",
    strict=True,
)
def test_no_duplicate_net_across_rules():
    findings = _analysis().engine.findings
    nets = [f.net for f in findings]
    assert len(nets) == len(set(nets))
