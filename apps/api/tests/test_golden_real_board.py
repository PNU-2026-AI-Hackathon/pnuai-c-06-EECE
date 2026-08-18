"""실제 보드 골든 테스트.

이 테스트가 깨지면 되돌린다. 예외 없다 (CLAUDE.md 10절).
기대값의 출처는 `tests/fixtures/esp32-c6-presence-smart-light.EXPECTED.md` 다.
숫자를 여기서 고치기 전에 그 문서를 먼저 고친다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prefab import catalog
from prefab.firmware import load_directory
from prefab.netlist.d356 import parse
from prefab.netlist.graph import Graph
from prefab.report import build_result
from prefab.runner import analyze
from prefab.types import Severity

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE = FIXTURES / "esp32-c6-presence-smart-light.d356"
FIRMWARE_DIR = FIXTURES / "esp32-c6-presence-smart-light.firmware"


def _analysis(with_firmware: bool = False):
    sources = load_directory(FIRMWARE_DIR) if with_firmware else None
    return analyze(
        FIXTURE.read_text(encoding="utf-8", errors="replace"),
        filename=FIXTURE.name,
        firmware_sources=sources,
    )


def _result(with_firmware: bool = False):
    a = _analysis(with_firmware)
    return build_result(
        check_id="chk_test01",
        created_at="2026-08-18T11:20:00Z",
        analysis=a,
        netlist_filename=FIXTURE.name,
        firmware_filename="firmware.zip" if with_firmware else None,
    )


# ------------------------------------------------------- 넷리스트만 (회귀 방지)

def test_netlist_only_still_finds_exactly_three():
    """펌웨어를 넣었다고 기존 3건이 사라지면 회귀다 (EXPECTED.md 3절)."""
    findings = _analysis().engine.findings
    assert [(f.rule, f.net) for f in findings] == [
        ("R12", "PRESENCE_3V3"),
        ("R12", "_IN_ACTIVE_LOW"),
        ("R11", "PRESENCE_3V3"),
    ]


def test_netlist_only_summary():
    s = _result()["summary"]
    assert (s["critical"], s["warning"]) == (2, 1)
    assert s["rules_run"] == 2
    assert s["rules_run"] + s["rules_skipped"] == s["rules_total"] == catalog.TOTAL


def test_parts_and_nets():
    nl = parse(FIXTURE)
    assert (nl.part_count, nl.net_count) == (10, 8)


def test_k1_pads_split_by_x_coordinate():
    assert len(Graph(parse(FIXTURE)).clusters("K1")) == 2


# ------------------------------------------------------- 펌웨어 포함

def test_with_firmware_findings_match_the_expected_doc():
    """치명 4 · 경고 2. R13 은 아직 채택 전이라 세지 않는다."""
    findings = _analysis(with_firmware=True).engine.findings
    assert [(f.rule, f.net) for f in findings] == [
        ("R07", None),
        ("R07", None),
        ("R12", "PRESENCE_3V3"),
        ("R12", "_IN_ACTIVE_LOW"),
        ("R08", "_IN_ACTIVE_LOW"),
        ("R11", "PRESENCE_3V3"),
    ]
    assert [f.severity for f in findings] == [
        Severity.CRITICAL, Severity.CRITICAL, Severity.CRITICAL,
        Severity.CRITICAL, Severity.WARNING, Severity.WARNING,
    ]


def test_with_firmware_summary():
    s = _result(with_firmware=True)["summary"]
    assert (s["critical"], s["warning"]) == (4, 2)
    assert s["rules_run"] == 4
    assert s["rules_run"] + s["rules_skipped"] == s["rules_total"]


def test_r07_targets_d3_and_d10_and_is_final():
    findings = [f for f in _analysis(with_firmware=True).engine.findings if f.rule == "R07"]
    assert len(findings) == 2
    assert {"D3", "D10"} == {f.claim.split("(")[0].split()[-1] for f in findings}
    assert all(f.unresolved_reason is None for f in findings)


def test_r08_targets_d5_only():
    findings = [f for f in _analysis(with_firmware=True).engine.findings if f.rule == "R08"]
    assert len(findings) == 1
    assert findings[0].net == "_IN_ACTIVE_LOW"


def test_unused_and_unwired_pins_stay_silent():
    """D0 · D1 · D4 · D6 는 회로도도 코드도 안 쓴다. 여기서 뜨면 오탐이다."""
    text = json.dumps(
        [f.to_dict() for f in _analysis(with_firmware=True).engine.findings],
        ensure_ascii=False,
    )
    for silk in ("D0", "D1", "D4", "D6"):
        assert f"{silk}(" not in text


def test_firmware_step_is_reported_as_done():
    step = _result(with_firmware=True)["pipeline"][2]
    assert step["status"] == "done"
    assert "D2" in step["detail"] and "D3" in step["detail"] and "D10" in step["detail"]


# ------------------------------------------------------- 계약 형태

def test_result_matches_the_api_contract_shape():
    result = _result()
    assert set(result) == {
        "check_id", "status", "created_at", "inputs",
        "summary", "pipeline", "findings", "netlist",
    }
    assert [s["step"] for s in result["pipeline"]] == [1, 2, 3, 4, 5, 6, 7]
    assert result["pipeline"][2]["status"] == "skipped"  # 펌웨어 미제출을 숨기지 않는다
    assert json.loads(json.dumps(result, ensure_ascii=False)) == result


def test_silk_and_gpio_ride_along_on_connections():
    """요청서 2-3 — 어느 SDIO 인지 응답만 보고 알 수 있어야 한다."""
    nets = {n["name"]: n for n in _result()["netlist"]["nets"]}
    u1 = next(c for c in nets["_IN_ACTIVE_LOW"]["connections"] if c["ref"] == "U1")
    assert (u1["pin"], u1["silk"], u1["gpio"]) == ("SDIO", "D5", 23)

    u1_d2 = next(c for c in nets["PRESENCE_3V3"]["connections"] if c["ref"] == "U1")
    assert (u1_d2["pin"], u1_d2["silk"], u1_d2["gpio"]) == ("LP-G", "D2", 2)


def test_parts_carry_resolved_pads_without_losing_pins():
    parts = {p["ref"]: p for p in _result()["netlist"]["parts"]}
    u1 = parts["U1"]
    assert len(u1["pins"]) == 18  # 기존 필드는 그대로다
    silks = [p["silk"] for p in u1["pads"]]
    assert silks.count("D3") == 1 and silks.count("D4") == 1 and silks.count("D5") == 1
    assert parts["U2"].get("pads") is None  # 모르는 부품에는 붙이지 않는다


def test_no_rule_is_silently_passed():
    for skipped in _analysis().engine.skipped:
        assert skipped.detail


def test_evidence_has_no_empty_placeholders():
    """값이 없으면 null. 빈 문자열이나 'N/A' 로 채우지 않는다 (계약)."""
    for f in _analysis(with_firmware=True).engine.findings:
        for ev in f.evidence:
            d = ev.to_dict()
            assert "" not in d.values()
            assert "N/A" not in d.values()


@pytest.mark.xfail(
    reason="알려진 문제 #1 — R11 과 R12 가 같은 네트에 중복으로 뜬다. dedup 미구현.",
    strict=True,
)
def test_no_duplicate_net_across_rules():
    nets = [f.net for f in _analysis().engine.findings]
    assert len(nets) == len(set(nets))
