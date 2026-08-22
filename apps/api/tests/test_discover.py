"""규칙 발견 — **LLM 이 낸 것을 코드가 거른다.**

이 파일이 지키는 것은 하나다: **지어낸 것이 화면에 안 들어간다.**

화면에 "우리가 못 봤을 수 있는 것" 이라고 적어 내보내는 자리라, 판정보다 오히려 더
엄해야 한다. 판정은 근거가 붙어 있어 사용자가 대조할 수 있지만, 후보는 "아직 모르는
것" 이라 대조할 기준이 없다.

여기 있는 것은 전부 **LLM 없이** 돈다. 검증은 순수 함수다.
"""

from __future__ import annotations

import pytest

from prefab.discover import Candidate, Citation, verify
from prefab.discover.propose import propose
from prefab.discover.run import covered_places, netlist_parts

FW = {"main.ino": "void setup(){\n  const int LED_PIN = D10;\n}\n"}


def _c(**kw) -> Candidate:
    base = dict(
        title="같은 이름의 핀 상수가 두 핀을 가리킴",
        why="배선이 바뀔 때 한쪽만 고치면 이렇게 됩니다.",
        citations=(Citation("firmware", "main.ino", "2", "const int LED_PIN = D10;"),),
    )
    return Candidate(**{**base, **kw})


# ── 통과해야 하는 것 ────────────────────────────────────────────────


def test_실재하는_자리를_가리키면_남는다():
    r = verify([_c()], firmware_sources=FW)
    assert len(r.kept) == 1 and not r.dropped


def test_줄을_한_칸_어긋나게_세도_봐준다():
    """모델이 1-based/0-based 를 헷갈리는 일이 흔하다. **인용이 맞으면 그건 진짜다.**"""
    r = verify([_c(citations=(Citation("firmware", "main.ino", "3", "const int LED_PIN = D10;"),))],
               firmware_sources=FW)
    assert len(r.kept) == 1, r.dropped


def test_경로가_달라도_파일_이름으로_찾는다():
    r = verify([_c(citations=(Citation("firmware", "src/main.ino", "2", "const int LED_PIN = D10;"),))],
               firmware_sources=FW)
    assert len(r.kept) == 1, r.dropped


# ── 버려야 하는 것 ──────────────────────────────────────────────────


def test_없는_파일을_가리키면_버린다():
    r = verify([_c(citations=(Citation("firmware", "nope.ino", "1", "x"),))], firmware_sources=FW)
    assert not r.kept and "파일이 없습니다" in r.dropped[0][1]


def test_없는_줄을_가리키면_버린다():
    r = verify([_c(citations=(Citation("firmware", "main.ino", "99", "x"),))], firmware_sources=FW)
    assert not r.kept and "99줄을 가리킵니다" in r.dropped[0][1]


def test_인용을_지어내면_버린다():
    """**제일 중요한 검사다.** 그럴듯한 문장은 모델이 잘 만든다."""
    r = verify([_c(citations=(Citation("firmware", "main.ino", "2", "pinMode(D3, INPUT);"),))],
               firmware_sources=FW)
    assert not r.kept and "인용한 내용이 없습니다" in r.dropped[0][1]


def test_가리키는_자리가_없으면_버린다():
    r = verify([_c(citations=())], firmware_sources=FW)
    assert not r.kept and "확인할 방법이 없습니다" in r.dropped[0][1]


@pytest.mark.parametrize("bad", [{"title": ""}, {"why": "  "}])
def test_제목이나_이유가_비면_버린다(bad):
    assert not verify([_c(**bad)], firmware_sources=FW).kept


def test_없는_부품을_가리키면_버린다():
    r = verify([_c(citations=(Citation("netlist", "U9", "D1"),))], netlist_parts={"U1": {"D1"}})
    assert not r.kept and "U9 부품이 없습니다" in r.dropped[0][1]


def test_없는_핀을_가리키면_버린다():
    r = verify([_c(citations=(Citation("netlist", "U1", "D42"),))], netlist_parts={"U1": {"D1"}})
    assert not r.kept and "D42 핀이 없습니다" in r.dropped[0][1]


def test_모르는_근거_종류는_버린다():
    r = verify([_c(citations=(Citation("느낌", "U1", None),))], netlist_parts={"U1": {"D1"}})
    assert not r.kept and "모르는 근거 종류" in r.dropped[0][1]


def test_이미_보고_있는_자리는_후보가_아니다():
    """새로운 것만 후보다. 이미 발견이 난 자리를 또 올리면 노이즈다."""
    r = verify(
        [_c(citations=(Citation("netlist", "U1", "D5"),))],
        netlist_parts={"U1": {"D5"}},
        covered_places={("U1", "D5")},
    )
    assert not r.kept and "이미 기존 규칙이 보고 있습니다" in r.dropped[0][1]


# ── 버린 것을 숨기지 않는다 ─────────────────────────────────────────


def test_버린_것도_이유와_함께_남는다():
    """**"두 개 찾았습니다" 와 "두 개만 말했습니다" 는 다르다** (헌법 2-4)."""
    r = verify(
        [_c(), _c(title="지어낸 것", citations=(Citation("firmware", "main.ino", "1", "없는 말"),))],
        firmware_sources=FW,
    )
    assert len(r.kept) == 1
    assert len(r.dropped) == 1 and r.dropped[0][0] == "지어낸 것"


# ── 모델을 못 불렀을 때 ─────────────────────────────────────────────


def test_키가_없으면_그렇게_말한다():
    """**부르지 않은 것과 못 부른 것은 다르다.** 조용히 빈 목록을 내면 안 된다."""
    out, why = propose(
        netlist_text="x", firmware_sources=None, catalog_rules=[], findings=[], api_key=""
    )
    assert out == [] and why and "ANTHROPIC_API_KEY" in why


# ── 검증 재료를 실제 분석에서 꺼내는가 ──────────────────────────────


def test_실측_보드에서_검증_재료가_나온다():
    """`netlist_parts` 와 `covered_places` 가 비면 검증이 통과만 시킨다."""
    from pathlib import Path

    from prefab.firmware import load_directory
    from prefab.runner import analyze

    F = Path(__file__).parent / "fixtures"
    a = analyze(
        (F / "esp32-c6-presence-smart-light.d356").read_text(encoding="utf-8"),
        filename="b.d356",
        bom_bytes=(F / "esp32-c6-presence-smart-light.bom.csv").read_bytes(),
        firmware_sources=load_directory(F / "esp32-c6-presence-smart-light.firmware"),
    )
    parts = netlist_parts(a.netlist)
    assert "U1" in parts and len(parts["U1"]) > 5, parts.keys()
    # 발견이 난 자리가 실제로 잡힌다
    assert covered_places(a.engine.findings), "기존 발견에서 자리를 하나도 못 읽었다"


# ── 표기가 어긋난 것과 지어낸 것은 다르다 ───────────────────────────
#
# 스키마로 칸을 나눠 줘도 모델은 곧잘 합쳐서 낸다 — `where: "main.ino:13"`.
# **형식이 어긋났다고 후보를 버리면 안 된다.** 우리가 거르려는 것은 지어낸 *내용*이지
# 표기법이 아니다. 실제로 이것 때문에 쓸 만한 후보 넷을 통째로 버렸다:
#
#     · 릴레이 핀 초기화 순서 역전 — pinMode(OUTPUT) 직후 기본 LOW 가 나가 활성-LOW 릴레이가 순간 ON
#     · PRESENCE 입력이 순수 INPUT — 센서 미장착 시 플로팅
#     ...넷 다 "파일이 없습니다" 로 버려졌다. 파일은 있었다.


def test_파일과_줄을_합쳐_와도_찾는다():
    r = verify([_c(citations=(Citation("firmware", "main.ino:2", None, "const int LED_PIN = D10;"),))],
               firmware_sources=FW)
    assert len(r.kept) == 1, r.dropped


def test_부품과_핀을_합쳐_와도_찾는다():
    r = verify([_c(citations=(Citation("netlist", "U1.D5", None),))], netlist_parts={"U1": {"D5"}})
    assert len(r.kept) == 1, r.dropped


def test_합쳐_왔어도_없는_자리는_그대로_버린다():
    """**형식만 봐주지 내용은 안 봐준다.**"""
    r = verify([_c(citations=(Citation("firmware", "main.ino:99", None, "x"),))], firmware_sources=FW)
    assert not r.kept and "99줄을 가리킵니다" in r.dropped[0][1]

    r2 = verify([_c(citations=(Citation("netlist", "U1.D42", None),))], netlist_parts={"U1": {"D5"}})
    assert not r2.kept and "D42 핀이 없습니다" in r2.dropped[0][1]


def test_칸이_제대로_나뉘어_오면_그대로_쓴다():
    """합치기 대응이 정상 표기를 망가뜨리면 안 된다."""
    r = verify([_c(citations=(Citation("firmware", "main.ino", "2", "const int LED_PIN = D10;"),))],
               firmware_sources=FW)
    assert len(r.kept) == 1, r.dropped
