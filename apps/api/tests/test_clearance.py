"""데이터시트로 경고를 해제하는 경로 (B-5).

이 제품이 파는 것이 여기 있다 — **측정 없이 문서로 푼다.**
전원이 5V인 부품이라고 출력도 5V인 것은 아니다. 그 사실 하나로 오탐이 사라진다.

동시에 이 파일은 **못 풀었을 때 무엇을 말하는지**를 고정한다.
"BOM 필요"는 BOM 을 이미 낸 사람에게는 거짓말이다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from prefab.datasheet.facts import CONF_HIGH, CONF_LOW, VOH_MAX, Fact, FactSet
from prefab.rules import r11_net_name_domain as r11
from prefab.rules import r12_cross_domain as r12
from prefab.types import Context, Verdict
from prefab.netlist.graph import Graph
from prefab.netlist.d356 import parse_text
from prefab.bom import parse_text as parse_bom
from tests._builder import board, rec

#: 5V 로 돌지만 출력은 3.3V 인 부품. 우리 보드의 mmWave 센서가 이 구조다.
#:
#: **여기 숫자는 시험용이다. 실제 데이터시트에서 확인한 값이 아니다.**
#: 이 파일이 고정하는 것은 값이 아니라 '''사실이 있을 때/없을 때 무엇을 말하는가''' 다.
#: 진짜 값은 `parts/*.json` 으로만 들어가고, 거기엔 출처가 붙어야 한다.
LEVEL_SHIFTED = "HLK-LD2410C"

BOM_CSV = f"Reference,MPN\nU2,{LEVEL_SHIFTED}\nU1,ESP32-C6-WROOM-1\n"


def _board() -> str:
    """U2 는 5V, U1 은 3.3V. 둘이 PRESENCE_3V3 로 직결돼 있다."""
    return board(
        rec("+5V", "U2", "VCC"),
        rec("PRESENCE_3V3", "U2", "OUT"),
        rec("+3V3", "U1", "3V3", x=0.5),
        rec("PRESENCE_3V3", "U1", "D2", x=0.5),
    )


def _fact(value, **kw) -> Fact:
    base = dict(
        mpn=LEVEL_SHIFTED, field=VOH_MAX, value=value, unit="V",
        table="Electrical Characteristics", page=3,
        quote="OUT high level output voltage 3.3V", confidence=CONF_HIGH,
    )
    return Fact(**{**base, **kw})


def _ctx(*, bom: bool = True, facts: FactSet | None = None) -> Context:
    return Context(
        netlist=Graph(parse_text(_board())),
        bom=parse_bom(BOM_CSV) if bom else None,
        datasheet=facts,
    )


def _one(module, ctx):
    found = module.check(ctx)
    assert len(found) == 1, f"발견이 {len(found)}건 — 이 보드는 1건이어야 한다"
    return found[0]


# ── 해제 ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("module", [r11, r12], ids=["R11", "R12"])
def test_출력이_3V3이면_경고가_해제된다(module):
    """전원 5V · 출력 3.3V. 토폴로지는 위험해 보이지만 데이터시트가 아니라고 답한다."""
    f = _one(module, _ctx(facts=FactSet([_fact(3.3)])))

    assert f.verdict is Verdict.PASS
    assert f.unresolved_reason is None, "풀렸는데 미결 사유가 남아 있다"


@pytest.mark.parametrize("module", [r11, r12], ids=["R11", "R12"])
def test_해제에는_반드시_출처가_붙는다(module):
    """근거 없는 해제는 사용자가 믿을 수 없다 (CLAUDE.md 2-1)."""
    f = _one(module, _ctx(facts=FactSet([_fact(3.3)])))

    cites = [e for e in f.evidence if e.kind == "datasheet"]
    assert len(cites) == 1
    assert (cites[0].mpn, cites[0].page) == (LEVEL_SHIFTED, 3)
    assert cites[0].quote, "인용문 없이 페이지 번호만 있으면 확인이 안 된다"
    assert "p.3" in f.suggestion


# ── 확정 ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("module", [r11, r12], ids=["R11", "R12"])
def test_출력이_5V면_미결이_아니라_확정된다(module):
    """데이터시트가 위험을 확인해 주면 그것도 답이다. 미결로 남기지 않는다."""
    f = _one(module, _ctx(facts=FactSet([_fact(5.0)])))

    assert f.verdict is Verdict.FAIL
    assert f.unresolved_reason is None, "확인이 끝났는데 미결로 남아 있다"
    assert any(e.kind == "datasheet" for e in f.evidence)


def test_R12는_한도를_넘는지로_판정한다():
    """3.6V 가 경계다. 매직넘버가 아니라 이름 있는 상수여야 한다."""
    assert r12.VOH_SAFE_MAX_V == 3.6
    edge = _one(r12, _ctx(facts=FactSet([_fact(r12.VOH_SAFE_MAX_V)])))
    over = _one(r12, _ctx(facts=FactSet([_fact(r12.VOH_SAFE_MAX_V + 0.1)])))
    assert edge.verdict is Verdict.PASS
    assert over.verdict is Verdict.FAIL


# ── 미결 — 무엇이 있으면 풀리는지 말한다 ──────────────────────────────


@pytest.mark.parametrize("module", [r11, r12], ids=["R11", "R12"])
def test_BOM이_없으면_BOM을_달라고_한다(module):
    f = _one(module, _ctx(bom=False))
    assert f.verdict is not Verdict.PASS
    assert "BOM" in f.unresolved_reason


@pytest.mark.parametrize("module", [r11, r12], ids=["R11", "R12"])
def test_BOM은_있는데_그_부품이_없으면_그렇게_말한다(module):
    """**BOM 을 이미 낸 사람에게 'BOM 필요'라고 하지 않는다.**"""
    ctx = Context(
        netlist=Graph(parse_text(_board())),
        bom=parse_bom("Reference,MPN\nU1,ESP32-C6-WROOM-1\n"),  # U2 가 없다
    )
    f = _one(module, ctx)
    reason = f.unresolved_reason
    assert "U2" in reason and "BOM 에 없거나" in reason
    assert "BOM 을 제출하면" not in reason, "이미 낸 BOM 을 또 내라고 한다"


@pytest.mark.parametrize("module", [r11, r12], ids=["R11", "R12"])
def test_부품번호는_있는데_데이터시트를_안_읽었으면_그렇게_말한다(module):
    f = _one(module, _ctx())
    assert LEVEL_SHIFTED in f.unresolved_reason
    assert "아직 읽지 않았습니다" in f.unresolved_reason


@pytest.mark.parametrize("module", [r11, r12], ids=["R11", "R12"])
def test_값이_있어도_출처가_없으면_판정하지_않는다(module):
    """출처 없는 값으로 해제하면 그게 오탐보다 나쁘다."""
    f = _one(module, _ctx(facts=FactSet([_fact(3.3, page=None, quote=None)])))
    assert f.verdict is not Verdict.PASS
    assert "출처가 없어" in f.unresolved_reason


@pytest.mark.parametrize("module", [r11, r12], ids=["R11", "R12"])
def test_확신이_낮은_값으로는_PASS를_내지_않는다(module):
    f = _one(module, _ctx(facts=FactSet([_fact(3.3, confidence=CONF_LOW)])))
    assert f.verdict is not Verdict.PASS
    assert "확신도가 낮아" in f.unresolved_reason


@pytest.mark.parametrize("module", [r11, r12], ids=["R11", "R12"])
def test_데이터시트에_값이_없다는_것도_답이다(module):
    """찾아봤지만 없더라 — 사용자는 이걸 알아야 다음 수를 정한다."""
    f = _one(module, _ctx(facts=FactSet([
        _fact(None, page=None, quote=None, confidence="none",
              reason="출력 전압 표가 없음")])))
    assert f.verdict is not Verdict.PASS
    assert "출력 전압 표가 없음" in f.unresolved_reason


@pytest.mark.parametrize("module", [r11, r12], ids=["R11", "R12"])
def test_숫자가_아닌_값으로는_비교하지_않는다(module):
    """'약 3.3V' 같은 문자열이 들어와도 조용히 통과시키지 않는다."""
    f = _one(module, _ctx(facts=FactSet([_fact("3.3V 내외")])))
    assert f.verdict is not Verdict.PASS


# ── 요약 집계 ───────────────────────────────────────────────────────


def test_해제된_발견은_심각도로_세지_않는다():
    """화면에 '심각 1건'과 '해제 1건'이 같이 뜨면 해제가 안 보인다."""
    from prefab.engine import EngineResult
    from prefab.report import build_summary

    f = _one(r12, _ctx(facts=FactSet([_fact(3.3)])))
    s = build_summary(parse_text(_board()), EngineResult(findings=[f], ran=["R12"]))
    assert (s["critical"], s["cleared"]) == (0, 1)


# ── 질문 자체가 틀린 경우 ────────────────────────────────────────────


def _relay_ctx(facts: FactSet | None = None) -> Context:
    """**실측 보드**를 그대로 쓴다.

    K1 은 전원 핀을 못 찾아 도메인을 **추론**으로만 안다. 그리고 K1 의 패드는
    릴레이 모듈의 `IN`, 즉 **입력**인데 넷리스트에는 핀 방향이 없어서
    구동하는 쪽인지 알 수 없다. 합성 보드로는 이 상황이 재현되지 않는다.
    """
    text = Path("tests/fixtures/esp32-c6-presence-smart-light.d356").read_text()
    return Context(
        netlist=Graph(parse_text(text)),
        bom=parse_bom("Reference,MPN\nK1,TONGLING JQC-3FF-S-Z\nU1,ESP32-C6-WROOM-1\n"),
        datasheet=facts,
    )


def _relay_finding(facts: FactSet | None = None):
    found = [f for f in r12.check(_relay_ctx(facts)) if f.net == "_IN_ACTIVE_LOW"]
    assert len(found) == 1
    return found[0]


def test_방향을_모르면_Voh를_약속하지_않는다():
    """구동하는 쪽인지도 모르는 부품에게 출력 전압을 묻는 건 영영 안 풀리는 질문이다."""
    reason = _relay_finding().unresolved_reason
    assert "구동하는지 입력으로 받는지" in reason
    assert "핀 방향과 내부 풀업" in reason
    assert "Voh" not in reason, "물어볼 수 없는 값을 확인하겠다고 약속한다"


def test_방향을_모르면_Voh가_있어도_해제하지_않는다():
    """입력 핀에 Voh 를 들이대면 잘못된 해제가 된다. 오탐보다 나쁘다."""
    facts = FactSet([Fact(
        mpn="TONGLING JQC-3FF-S-Z", field=VOH_MAX, value=3.3, unit="V",
        table="EC", page=2, quote="3.3V", confidence=CONF_HIGH)])
    f = _relay_finding(facts)
    assert f.verdict is not Verdict.PASS
    assert not any(e.kind == "datasheet" for e in f.evidence)


def test_이미_낸_BOM을_또_내라고_하지_않는다():
    """부품번호를 아는데 '부품번호를 제출하면' 이라고 쓰면,
    사용자는 자기가 뭘 빠뜨렸는지 찾다가 시간을 버린다."""
    f = _relay_finding()
    assert "JQC-3FF-S-Z" in f.suggestion
    assert "제출하면" not in f.suggestion


def test_BOM이_없을_때는_BOM을_달라고_한다():
    ctx = Context(netlist=_relay_ctx().netlist, bom=None, datasheet=None)
    f = [x for x in r12.check(ctx) if x.net == "_IN_ACTIVE_LOW"][0]
    assert "BOM으로 제출하면" in f.suggestion


# ── io_level — 모듈 데이터시트는 Voh 규격을 잘 안 준다 ────────────────


def _io_fact(value=3.3, **kw):
    from prefab.datasheet.facts import IO_LEVEL

    base = dict(
        mpn=LEVEL_SHIFTED, field=IO_LEVEL, value=value, unit="V",
        table="Table 2 (Interface)", page=17,
        quote="A GPIO, IO level 3.3V", confidence=CONF_HIGH,
    )
    return Fact(**{**base, **kw})


@pytest.mark.parametrize("module", [r11, r12], ids=["R11", "R12"])
def test_Voh가_없어도_IO_레벨로_해제된다(module):
    """실측에서 나온 문제다. `HLK-LD2410C` 매뉴얼에는 Voh 규격 표가 없고
    "IO level 3.3V" 만 있다. IO 레일이 3.3V 면 그 핀 출력이 5V 로 올라갈 수 없다."""
    f = _one(module, _ctx(facts=FactSet([_io_fact()])))
    assert f.verdict is Verdict.PASS
    assert f.unresolved_reason is None


def test_IO_레벨로_해제하면_Voh라고_말하지_않는다():
    """없는 규격을 있다고 말하면 안 된다. 사람이 그걸 해서 이 항목이 생겼다."""
    f = _one(r12, _ctx(facts=FactSet([_io_fact()])))
    assert "IO 로직 레벨" in f.claim
    assert "출력 하이 전압" not in f.claim


def test_Voh가_있으면_그쪽을_먼저_쓴다():
    """`voh_max` 가 더 직접적인 규격이다. 둘 다 있으면 그걸 쓴다."""
    f = _one(r12, _ctx(facts=FactSet([_fact(3.3), _io_fact(3.3)])))
    assert "출력 하이 전압" in f.claim


def test_아무것도_없으면_Voh를_달라고_한다():
    """'IO 레벨을 주세요' 보다 'Voh 를 주세요' 가 쓸모 있는 안내다."""
    f = _one(r12, _ctx())
    assert "출력 하이 전압(Voh)" in f.unresolved_reason


@pytest.mark.parametrize("module", [r11, r12], ids=["R11", "R12"])
def test_IO_레벨도_출처가_없으면_안_쓴다(module):
    f = _one(module, _ctx(facts=FactSet([_io_fact(page=None, quote=None)])))
    assert f.verdict is not Verdict.PASS
