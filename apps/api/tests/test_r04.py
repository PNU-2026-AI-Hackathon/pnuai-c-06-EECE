"""R04 — 외부 부품 출력이 GPIO 입력 최대 정격 초과.

R12 와 묻는 것이 다르다. R12 는 **전원 도메인**을 넷리스트로 보고,
R04 는 **양쪽 데이터시트 숫자**를 직접 비교한다.

그래서 R04 는 양쪽 데이터시트가 다 있어야 말을 한다. 하나라도 없으면
조용히 있는다 — 그 자리는 R12 가 이미 미결로 말하고 있고, 여기서 또
말하면 같은 네트에 경고가 두 번 쌓인다 (CLAUDE.md 2-3).
"""

from __future__ import annotations

import pytest

from prefab.bom import parse_text as parse_bom
from prefab.datasheet.facts import (
    CONF_HIGH,
    CONF_LOW,
    IO_LEVEL,
    VIN_ABSOLUTE_MAX,
    Fact,
    FactSet,
)
from prefab.netlist.d356 import parse_text
from prefab.netlist.graph import Graph
from prefab.rules import r04_input_overvoltage as r04
from prefab.types import Context, Verdict
from tests._builder import board, rec

SENSOR, MCU = "SENSOR-5V", "MCU-CHIP"
BOM = f"Reference,MPN\nU2,{SENSOR}\nU1,{MCU}\n"


def _board() -> str:
    return board(
        rec("+5V", "U2", "VCC"),
        rec("SIG", "U2", "OUT"),
        rec("+3V3", "U1", "3V3", x=0.5),
        rec("SIG", "U1", "D2", x=0.5),
    )


def _fact(mpn, field, value, **kw) -> Fact:
    base = dict(
        mpn=mpn, field=field, value=value, unit="V", table="Electrical Characteristics",
        page=5, quote="datasheet row", confidence=CONF_HIGH,
    )
    return Fact(**{**base, **kw})


def _ctx(*facts: Fact) -> Context:
    return Context(
        netlist=Graph(parse_text(_board())),
        bom=parse_bom(BOM),
        datasheet=FactSet(facts) if facts else None,
    )


def _run(*facts: Fact):
    return r04.check(_ctx(*facts))


# ── 양성 ────────────────────────────────────────────────────────────


def test_출력이_절대_최대를_넘으면_잡는다():
    f = _run(
        _fact(SENSOR, IO_LEVEL, 5.0),
        _fact(MCU, VIN_ABSOLUTE_MAX, 3.6),
    )[0]
    assert f.rule == "R04" and f.verdict is Verdict.FAIL
    assert f.net == "SIG"
    assert "5V" in f.claim and "3.6V" in f.claim
    assert "1.4V 초과" in f.claim


def test_양쪽_데이터시트를_근거로_단다():
    """추정이 아니라 두 문서의 값이라는 게 이 규칙의 전부다."""
    f = _run(_fact(SENSOR, IO_LEVEL, 5.0), _fact(MCU, VIN_ABSOLUTE_MAX, 3.6))[0]
    cites = [e for e in f.evidence if e.kind == "datasheet"]
    assert {c.mpn for c in cites} == {SENSOR, MCU}
    assert any(e.kind == "netlist" for e in f.evidence)


def test_고장이라고_말한다():
    """절대 최대 정격은 '동작 이상'이 아니라 '파손' 기준이다."""
    f = _run(_fact(SENSOR, IO_LEVEL, 5.0), _fact(MCU, VIN_ABSOLUTE_MAX, 3.6))[0]
    assert "파손" in f.suggestion


def test_핀_방향을_몰라도_판정한다():
    """A 가 5V 를 낼 수 있고 B 가 3.6V 까지만 견디면, 누가 구동하든 위험하다."""
    assert len(_run(_fact(SENSOR, IO_LEVEL, 5.0), _fact(MCU, VIN_ABSOLUTE_MAX, 3.6))) == 1


# ── 음성 ────────────────────────────────────────────────────────────


def test_한도_안이면_아무_말도_안_한다():
    assert _run(_fact(SENSOR, IO_LEVEL, 3.3), _fact(MCU, VIN_ABSOLUTE_MAX, 3.6)) == []


def test_경계값은_통과다():
    """3.6V 까지가 절대 최대다. 같은 값이면 넘은 게 아니다."""
    assert _run(_fact(SENSOR, IO_LEVEL, 3.6), _fact(MCU, VIN_ABSOLUTE_MAX, 3.6)) == []


def test_자기_자신과는_비교하지_않는다():
    both = [_fact(SENSOR, IO_LEVEL, 5.0), _fact(SENSOR, VIN_ABSOLUTE_MAX, 3.6)]
    assert _run(*both) == []


# ── 미해결 — 조용히 있는 것이 맞다 ───────────────────────────────────


def test_데이터시트가_없으면_조용히_있는다():
    """R12 가 이미 그 네트를 미결로 말하고 있다. 여기서 또 말하면 중복이다."""
    assert _run() == []


def test_한쪽만_알면_조용히_있는다():
    assert _run(_fact(SENSOR, IO_LEVEL, 5.0)) == []
    assert _run(_fact(MCU, VIN_ABSOLUTE_MAX, 3.6)) == []


def test_확신도가_낮은_값으로는_판정하지_않는다():
    """low 로 CRITICAL 을 내면 그게 최악의 오탐이다."""
    assert _run(
        _fact(SENSOR, IO_LEVEL, 5.0, confidence=CONF_LOW),
        _fact(MCU, VIN_ABSOLUTE_MAX, 3.6),
    ) == []


def test_출처_없는_값으로는_판정하지_않는다():
    assert _run(
        _fact(SENSOR, IO_LEVEL, 5.0, page=None, quote=None),
        _fact(MCU, VIN_ABSOLUTE_MAX, 3.6),
    ) == []


def test_BOM이_없으면_엔진이_건너뛴다():
    """NEEDS 에 bom 이 있다. 부품번호를 모르면 데이터시트를 못 찾는다."""
    assert "bom" in r04.NEEDS
    ctx = Context(netlist=Graph(parse_text(_board())), bom=None)
    assert ctx.missing(r04.NEEDS) == ["bom"]
