"""검사 결과 커밋 간 비교 (F-1).

**드리프트를 R10 없이 보여주는 자리다.** 회로도를 고치고 코드를 안 고치면
같은 엔진이 두 입력에 다른 발견을 낸다. 그 차이가 곧 드리프트다.

이 파일이 지키는 것은 두 가지다.

1. 실제 드리프트를 **잡는가** — 센서 배선을 D2 → D4 로 옮긴 픽스처가 그 증거다
2. 아무것도 안 바꿨을 때 **조용한가** — 여기서 시끄러우면 아무도 안 읽는다
"""

from __future__ import annotations

import json
from pathlib import Path

from prefab.diff import diff_results, finding_key, format_diff
from prefab.firmware import load_directory
from prefab.report import build_result
from prefab.runner import analyze

FIXTURES = Path(__file__).parent / "fixtures"
BEFORE = FIXTURES / "esp32-c6-presence-smart-light.d356"
#: 회로도만 고친 판. 두 줄 차이다 — 센서 OUT 이 D2 에서 D4 로 옮겨갔다.
AFTER = FIXTURES / "esp32-c6-presence-smart-light.moved-to-d4.d356"
FIRMWARE_DIR = FIXTURES / "esp32-c6-presence-smart-light.firmware"


def _result(netlist: Path, *, with_firmware: bool = True) -> dict:
    a = analyze(
        netlist.read_text(encoding="utf-8", errors="replace"),
        filename=netlist.name,
        firmware_sources=load_directory(FIRMWARE_DIR) if with_firmware else None,
    )
    return build_result(
        check_id="chk_diff",
        created_at="2026-08-19T00:00:00Z",
        analysis=a,
        netlist_filename=netlist.name,
        firmware_filename="firmware.zip" if with_firmware else None,
    )


def _rules(findings) -> list[str]:
    return sorted(f["rule"] for f in findings)


# ── 조용해야 할 때 ──────────────────────────────────────────────────


def test_같은_입력이면_아무것도_안_뜬다():
    """여기서 시끄러우면 PR 마다 노이즈가 쌓이고 도구가 꺼진다 (헌법 2-3)."""
    r = _result(BEFORE)
    d = diff_results(r, r)
    assert d.quiet
    assert d.added == [] and d.removed == [] and d.changed == []
    assert "드리프트 없음" in format_diff(d)


def test_문구만_달라진_발견은_새_발견이_아니다():
    """근거 문구를 다듬는 것은 헌법 11절이 시키는 일이다. 그 대가를 여기서 막는다."""
    before = _result(BEFORE)
    after = json.loads(json.dumps(before))
    for f in after["findings"]:
        f["claim"] = "(문구를 다듬었습니다) " + f["claim"]
        f["suggestion"] = "다른 제안"
    d = diff_results(before, after)
    assert d.quiet


# ── 실제 드리프트 ───────────────────────────────────────────────────


def test_회로도만_고치면_코드가_안_따라온_것이_뜬다():
    """센서 OUT 을 D2 → D4 로 옮겼다. 코드는 그대로 D2 를 읽는다.

    이것이 이 제품이 파는 장면이다 — 컴파일도 되고 DRC 도 통과하는데 안 켜지는 보드.
    """
    d = diff_results(_result(BEFORE), _result(AFTER))

    # 코드가 쓰는 D2 가 회로도에서 떨어져 나갔다
    assert "R07" in _rules(d.added)
    r07 = next(f for f in d.added if f["rule"] == "R07")
    assert "D2" in r07["claim"]

    # 새로 배선된 D4 는 코드가 안 쓴다
    assert "R08" in _rules(d.added)
    r08 = next(f for f in d.added if f["rule"] == "R08")
    assert "D4" in r08["claim"]


def test_새_치명_발견이_CI를_빨간불로_만든다():
    d = diff_results(_result(BEFORE), _result(AFTER))
    assert d.blocking, "새 치명 발견이 있으면 막아야 한다"
    assert all(f["severity"] == "CRITICAL" for f in d.blocking)


def test_고쳐진_것도_같이_보여준다():
    """나빠진 것만 보여주면 고친 사람이 확인할 자리가 없다.

    되돌린 방향에서는 드리프트 두 건(R07·R08)이 사라진다. R12 는 사라지지 않고
    **자리를 옮긴다** — 5V 센서가 3.3V 핀에 직결된 사실 자체는 배선을 옮겨도
    그대로이기 때문이다. 그것까지 '고쳤다'로 세면 숫자가 거짓말을 한다.
    """
    d = diff_results(_result(AFTER), _result(BEFORE))
    assert {"R07", "R08"} <= set(_rules(d.removed)), _rules(d.removed)
    assert _rules(d.added) == ["R12"], "R12 는 D4 → D2 로 자리만 옮긴다"


# ── 신원 ────────────────────────────────────────────────────────────


def test_같은_자리_같은_규칙이면_같은_발견이다():
    f = {
        "rule": "R12", "net": "SIG", "claim": "무엇이든",
        "evidence": [{"kind": "netlist", "text": "", "highlight": ["U1.D2", "5V_BUS"]}],
    }
    g = {**f, "claim": "다른 문구", "suggestion": "다른 제안"}
    assert finding_key(f) == finding_key(g)


def test_자리가_다르면_다른_발견이다():
    base = {"rule": "R12", "net": "SIG",
            "evidence": [{"kind": "netlist", "text": "", "highlight": ["U1.D2"]}]}
    moved = {"rule": "R12", "net": "SIG",
             "evidence": [{"kind": "netlist", "text": "", "highlight": ["U1.D4"]}]}
    assert finding_key(base) != finding_key(moved)


# ── 정직함 ──────────────────────────────────────────────────────────


def test_규칙_수가_달라지면_그_사실을_적는다():
    """규칙을 추가한 PR 이 '보드가 나빠졌다'로 읽히면 안 된다."""
    before = _result(BEFORE)
    after = json.loads(json.dumps(before))
    after["summary"]["rules_run"] = before["summary"]["rules_run"] + 1
    d = diff_results(before, after)
    assert d.notes and "규칙이 늘어서" in d.notes[0]
    assert "⚠" in format_diff(d)


def test_못_보는_것을_보고서에_같이_적는다():
    """이 비교는 PR 이전부터 있던 문제를 안 보여준다. 숨기지 않는다."""
    text = format_diff(diff_results(_result(BEFORE), _result(AFTER)))
    assert "이 비교가 못 보는 것" in text


def test_판정만_달라진_것은_따로_센다():
    before = _result(BEFORE)
    after = json.loads(json.dumps(before))
    after["findings"][0]["verdict"] = "PASS"
    d = diff_results(before, after)
    assert len(d.changed) == 1
    assert d.added == [] and d.removed == []
    assert d.changed[0].cleared
    assert "해제됨" in format_diff(d)


# ── 해제된 항목을 무겁게 표시하지 않는다 ─────────────────────────────


def test_해제된_발견은_등급_옆에_해제됨이_붙는다():
    """데이터시트로 지운 항목이 🔴 아래에 그냥 `(CRITICAL)` 로 나가고 있었다.

    **막지도 않는 항목을 제일 무겁게 보여주는 셈이라** 읽는 사람이 코멘트를 못 믿게 된다.
    막는 기준(`blocking`)은 이미 판정까지 보고 있었는데 표시만 안 따라왔다.
    """
    from prefab.diff import diff_results, format_diff

    before = {"findings": []}
    after = {
        "findings": [
            {"rule": "R12", "net": "SIG", "severity": "CRITICAL", "verdict": "PASS",
             "claim": "데이터시트로 풀렸다", "evidence": []},
            {"rule": "R07", "net": "SIG2", "severity": "CRITICAL", "verdict": "FAIL",
             "claim": "진짜 문제다", "evidence": []},
        ]
    }
    d = diff_results(before, after)
    text = format_diff(d, before_label="main", after_label="이 PR")

    assert "(CRITICAL · 해제됨)" in text, text
    # 해제된 것은 막지 않는다 — 막는 것은 FAIL 뿐이다
    assert len(d.blocking) == 1, d.blocking
    assert d.blocking[0]["rule"] == "R07"


def test_해제된_것만_있으면_막지_않는다():
    from prefab.diff import diff_results

    after = {
        "findings": [
            {"rule": "R12", "net": "SIG", "severity": "CRITICAL", "verdict": "PASS",
             "claim": "풀렸다", "evidence": []}
        ]
    }
    assert diff_results({"findings": []}, after).blocking == []
