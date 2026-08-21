"""REV1 → REV2 — 우리 도구가 짚은 자리를 고치니 조용해진다.

**이 파일이 붙잡는 것은 고리 하나다.**

    도구가 짚는다  →  사람이 고친다  →  도구가 조용해진다

2026-08-21 에 실제로 일어난 일이다. 하드웨어 담당이 "LED가 ON은 되는데 OFF가
안된다" 고 보고했고, R15 가 그 네트를 짚었고, 2N3904 레벨시프트로 고쳤다.
**PCB(REV1)는 이미 발주된 뒤였다** — 그래서 REV2 는 손으로 개조해야 한다.
발주 전에 이걸 잡는 것이 이 제품이 하려는 일 그대로다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from prefab.datasheet.seed import seed_facts
from prefab.datasheet.store import FactStore
from prefab.firmware import load_directory
from prefab.runner import analyze

FIXTURES = Path(__file__).parent / "fixtures"
PARTS = Path(__file__).parent.parent / "parts"

REV1 = FIXTURES / "esp32-c6-presence-smart-light.d356"
REV1_FW = FIXTURES / "esp32-c6-presence-smart-light.v2.firmware"
REV2 = FIXTURES / "esp32-c6-presence-smart-light.rev2.net.xml"
REV2_FW = FIXTURES / "esp32-c6-presence-smart-light.rev2.firmware"
BOM = FIXTURES / "esp32-c6-presence-smart-light.bom.csv"


@pytest.fixture()
def facts(tmp_path) -> FactStore:
    """커밋된 사실만으로 만든 DB. 서버가 기동 때 하는 것과 같다."""
    store = FactStore(tmp_path / "facts.db")
    seed_facts(PARTS, store)
    return store


def _run(netlist: Path, firmware: Path, facts: FactStore):
    return analyze(
        netlist.read_text(encoding="utf-8", errors="replace"),
        filename=netlist.name,
        bom_bytes=BOM.read_bytes(),
        firmware_sources=load_directory(firmware),
        fact_store=facts,
    )


def _open_rules(analysis) -> set[str]:
    """해제되지 않고 남은 발견의 규칙들."""
    return {f.rule for f in analysis.engine.findings if f.verdict.value != "PASS"}


def test_REV1_에서_두_가지를_짚는다(facts):
    """`_IN_ACTIVE_LOW` 한 네트에 두 이야기가 있다 — 방향이 서로 반대다.

    R15 나가는 쪽 : MCU 의 3.3V 가 K1 의 문턱에 못 미친다 → **안 꺼진다**
    R04 들어오는 쪽 : K1 의 5V 가 MCU 의 절대 최대(3.6V)를 넘는다 → **위험하다**
    """
    rules = _open_rules(_run(REV1, REV1_FW, facts))
    assert "R15" in rules, rules
    assert "R04" in rules, rules


def test_REV1_의_R15_는_확정이다(facts):
    """`io_level` 실측이 들어온 뒤로는 "확인 필요" 가 아니라 "안 된다" 다."""
    found = [f for f in _run(REV1, REV1_FW, facts).engine.findings if f.rule == "R15"]
    assert len(found) == 1
    f = found[0]
    assert f.verdict.value == "FAIL"
    assert "하이가 되지 않습니다" in f.claim, f.claim
    # 근거가 데이터시트(실측)에서 온다는 것이 보여야 한다
    assert "datasheet" in {e.kind for e in f.evidence}


def test_REV2_에서_조용해진다(facts):
    """트랜지스터가 두 문제를 **동시에** 없앤다.

    D5 는 이제 베이스만 몬다(상대가 수동 소자뿐) → R15 대상이 아니다.
    K1.IN 은 MCU 와 더 이상 같은 네트가 아니다 → R04 대상이 아니다.
    """
    a = _run(REV2, REV2_FW, facts)
    rules = _open_rules(a)
    assert rules == set(), [(f.rule, f.net, f.claim[:60]) for f in a.engine.findings]


def test_REV2_에서도_규칙은_다_돌았다(facts):
    """**조용한 것과 안 돈 것은 다르다.** 입력이 모자라서 조용하면 그건 성과가 아니다."""
    a = _run(REV2, REV2_FW, facts)
    assert a.engine.skipped == [], a.engine.skipped


def test_REV2_넷리스트가_문서대로다(facts):
    """손으로 옮긴 파일이라 오타 하나가 결론을 바꾼다. 핵심 연결만 다시 확인한다."""
    a = _run(REV2, REV2_FW, facts)
    nets = a.netlist.nets
    assert {"Q1_BASE_DRIVE", "Q1_BASE", "RELAY_IN_NET"} <= set(nets)
    # D5 는 이제 릴레이가 아니라 베이스 저항으로 간다
    assert {p.ref for p in nets["Q1_BASE_DRIVE"]} == {"U1", "R4"}
    # 릴레이 IN 에 MCU 가 없다 — 이것이 고쳐진 지점이다
    assert "U1" not in {p.ref for p in nets["RELAY_IN_NET"]}
    # R3 풀업이 5V 로 갔다
    assert "R3" in {p.ref for p in nets["5V_BUS"]}
