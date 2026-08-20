"""데이터시트 LLM 추출 (B-3).

**키 없이 전부 돈다.** 가짜 클라이언트를 넣기 때문이다 — 그게 `Client` 프로토콜의 이유다.

여기서 지키려는 것은 하나다. **LLM 이 지어낸 출처가 DB 에 못 들어가는 것.**
모델이 "17쪽에 이렇게 써 있다"고 하면 코드가 17쪽 원문을 실제로 확인한다.
`결정_기록.md` D-1 "AI 가 제안하고 결정적 코드가 검증한다" 를 추출에 적용한 것이다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

from prefab.datasheet.extract import (
    MODEL,
    Extraction,
    ExtractionError,
    Page,
    build_prompt,
    extract,
)
from prefab.datasheet.facts import (
    CONF_HIGH,
    CONF_NONE,
    OUTPUT_TYPE,
    TIER_OFFICIAL,
    VCC_NOMINAL,
    VOH_MAX,
)
from prefab.datasheet.store import FactStore

#: 실제 HLK-LD2410C 매뉴얼 17쪽에서 옮긴 문장이다.
PAGE_17 = """7. Performance and electrical parameters
Operating Voltage    DC 5V, power supply capacity>200mA
Interface            A GPIO, IO level 3.3V
                     A UART
Ambient temperature  -40 ~ 85℃
Table 2 Performance and electrical parameters table"""

PAGES = [Page(number=17, text=PAGE_17)]
URL = "https://example.invalid/ld2410c.pdf"


# ── 가짜 클라이언트 ─────────────────────────────────────────────────


@dataclass
class _Block:
    text: str
    type: str = "text"


@dataclass
class _Response:
    content: list[_Block]
    stop_reason: str = "end_turn"


class FakeClient:
    """모델이 이렇게 답했다고 치고 돌린다. 보낸 요청도 기록한다."""

    def __init__(self, reply: Any, *, stop_reason: str = "end_turn") -> None:
        text = reply if isinstance(reply, str) else json.dumps(reply)
        self._response = _Response([_Block(text)], stop_reason=stop_reason)
        self.sent: dict[str, Any] = {}

    @property
    def messages(self):
        return self

    def create(self, **kwargs: Any) -> _Response:
        self.sent = kwargs
        return self._response


def _item(**kw: Any) -> dict[str, Any]:
    """모델이 돌려주는 한 항목의 기본 모양."""
    base = {
        "field": VOH_MAX,
        "value_number": 3.3,
        "value_text": None,
        "unit": "V",
        "table": "Table 2 Performance and electrical parameters table",
        "page": 17,
        "quote": "A GPIO, IO level 3.3V",
        "confidence": CONF_HIGH,
        "reason": None,
    }
    return {**base, **kw}


def _run(items: list[dict[str, Any]], **kw: Any) -> Extraction:
    client = FakeClient({"facts": items})
    return extract(
        client, mpn="HLK-LD2410C", pages=PAGES, source_url=URL,
        source_tier=TIER_OFFICIAL, **kw,
    )


# ── 요청이 스키마를 강제하는가 ───────────────────────────────────────


def test_자유_텍스트로_받지_않는다():
    """스키마를 강제하지 않으면 판정에 쓸 수 없는 값이 들어온다 (헌법 2-1)."""
    client = FakeClient({"facts": []})
    extract(client, mpn="X", pages=PAGES, source_url=URL)

    fmt = client.sent["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["schema"]["additionalProperties"] is False
    assert client.sent["model"] == MODEL


def test_본문에_쪽_번호가_붙는다():
    """번호가 없으면 출처를 검증할 방법이 없다."""
    prompt = build_prompt("X", PAGES)
    assert "=== 17쪽 ===" in prompt
    assert "A GPIO, IO level 3.3V" in prompt


def test_본문이_없으면_부르지_않는다():
    with pytest.raises(ValueError):
        extract(FakeClient({"facts": []}), mpn="X", pages=[], source_url=URL)


def test_모르는_출처_등급은_거절한다():
    with pytest.raises(ValueError):
        extract(FakeClient({"facts": []}), mpn="X", pages=PAGES,
                source_url=URL, source_tier="아무거나")


# ── 검증 — 이 파일의 핵심 ───────────────────────────────────────────


def test_원문에_있는_인용은_통과한다():
    r = _run([_item()])
    assert r.ok
    assert r.facts[0]["value"] == 3.3
    assert r.facts[0]["page"] == 17


def test_지어낸_인용은_버린다():
    """모델이 그럴듯한 문장을 만들어 낼 수 있다. 원문에 없으면 값이 아니다."""
    r = _run([_item(quote="Output high voltage 3.3V typical")])
    assert r.facts == []
    assert "지어졌습니다" in r.dropped[0].why


def test_없는_쪽을_대면_버린다():
    r = _run([_item(page=3)])
    assert r.facts == []
    assert "3쪽은 넘겨준 본문에 없습니다" in r.dropped[0].why


def test_값만_말하고_출처를_안_대면_버린다():
    r = _run([_item(page=None, quote=None)])
    assert r.facts == []
    assert "몇 쪽 어느 문장인지" in r.dropped[0].why


def test_줄바꿈과_공백_차이는_봐준다():
    """PDF 에서 뽑은 글자는 공백이 제멋대로다. 그것 때문에 진짜를 버리면 안 된다."""
    r = _run([_item(quote="A GPIO,\n  IO   level 3.3V")])
    assert r.ok and len(r.facts) == 1


def test_글자_레이어가_공백을_잃어버려도_통과한다():
    """**실측에서 나온 경우다.** HLK-LD2410C 매뉴얼 17쪽은 화면에
    `A GPIO, IO level 3.3V` 로 보이는데, 글자 레이어에서 뽑으면
    `AGPIO,IO level 3.3V` 다. 공백만 줄이는 정규화로는 진짜 인용문이
    지어낸 것으로 판정됐다. 공백은 이 검증에서 아무 뜻도 없다.
    """
    mangled = [Page(number=17, text="AGPIO,IO level 3.3V\nDC 5V,power supplycapacity>200mA")]
    client = FakeClient({"facts": [_item(quote="A GPIO, IO level 3.3V")]})
    r = extract(client, mpn="X", pages=mangled, source_url=URL)
    assert r.ok and len(r.facts) == 1


def test_공백_말고는_봐주지_않는다():
    """한 글자라도 다르면 버린다. '3.3V' 와 '3.5V' 는 다른 값이다."""
    r = _run([_item(quote="A GPIO, IO level 3.5V")])
    assert r.facts == []


def test_값이_없다는_것도_사실이다():
    r = _run([_item(field=OUTPUT_TYPE, value_number=None, page=None, quote=None,
                    confidence=CONF_NONE, reason="매뉴얼에 명시 없음")])
    assert r.ok
    assert r.facts[0]["value"] is None
    assert r.facts[0]["reason"] == "매뉴얼에 명시 없음"


def test_이유_없는_모름은_버린다():
    r = _run([_item(field=OUTPUT_TYPE, value_number=None, page=None,
                    quote=None, confidence=CONF_NONE, reason=None)])
    assert r.facts == []
    assert "왜 없는지" in r.dropped[0].why


def test_하나가_떨어져도_나머지는_남는다():
    r = _run([
        _item(),
        _item(field=VCC_NOMINAL, value_number=5.0,
              quote="DC 5V, power supply capacity>200mA"),
        _item(field="vih_min", value_number=2.0, quote="지어낸 문장"),
    ])
    assert len(r.facts) == 2 and len(r.dropped) == 1


def test_문자열_값도_다룬다():
    r = _run([_item(field=OUTPUT_TYPE, value_number=None,
                    value_text="A GPIO", quote="Interface")])
    assert r.facts[0]["value"] == "A GPIO"


# ── 실패 ────────────────────────────────────────────────────────────


def test_거절은_사실_없음과_다르다():
    """모델이 거절한 것과 '데이터시트에 값이 없다'는 완전히 다른 상태다."""
    with pytest.raises(ExtractionError, match="거절"):
        extract(FakeClient({"facts": []}, stop_reason="refusal"),
                mpn="X", pages=PAGES, source_url=URL)


def test_JSON이_아니면_죽지_않고_말한다():
    with pytest.raises(ExtractionError, match="JSON"):
        extract(FakeClient("이건 JSON 이 아닙니다"), mpn="X",
                pages=PAGES, source_url=URL)


# ── 저장기까지 이어지는가 ───────────────────────────────────────────


def test_추출_결과를_저장기가_그대로_받는다(tmp_path):
    """추출과 저장 사이에 손으로 옮기는 단계가 있으면 거기서 값이 상한다."""
    r = _run([
        _item(),
        _item(field=VCC_NOMINAL, value_number=5.0,
              quote="DC 5V, power supply capacity>200mA"),
    ])
    store = FactStore(tmp_path / "t.db")
    report = store.save(r.payload)

    assert report.ok and report.stored == 2
    f = store.lookup(["HLK-LD2410C"]).facts.usable("HLK-LD2410C", VOH_MAX)
    assert f.value == 3.3 and f.page == 17


def test_검증에서_떨어진_것은_저장기까지_가지_않는다(tmp_path):
    """저장기도 출처를 요구하지만, 지어낸 인용은 출처가 '있어' 보인다.
    원문 대조는 여기서만 할 수 있다."""
    r = _run([_item(quote="그럴듯하지만 원문에 없는 문장")])
    store = FactStore(tmp_path / "t.db")
    store.save(r.payload)
    assert store.size() == (0, 0)


# ── .env 읽기 — 파이썬은 자동으로 안 읽는다 ──────────────────────────


def test_env_파일을_찾아_올린다(tmp_path, monkeypatch):
    """Vite 는 `.env` 를 읽고 파이썬은 안 읽는다. 그 차이가 사람을 헷갈리게 한다."""
    from prefab.__main__ import _load_env

    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=가짜\n# 주석\n빈줄무시\n")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert _load_env(tmp_path) is not None
    import os
    assert os.environ["ANTHROPIC_API_KEY"] == "가짜"


def test_BOM_이_붙은_env_도_읽는다(tmp_path, monkeypatch):
    """윈도우 PowerShell 5.1 의 `Out-File -Encoding utf8` 은 **BOM 을 붙인다.**

    그냥 `utf-8` 로 읽으면 첫 줄 이름이 `\ufeffANTHROPIC_API_KEY` 가 되어,
    화면에는 "환경 파일: ...\.env" 와 "키를 찾지 못했습니다" 가 **같이** 뜬다.
    파일은 찾았다고 하는데 키는 없다고 하니 무엇이 잘못됐는지 안 보인다.
    실제로 한 번 여기서 막혔다.
    """
    from prefab.__main__ import _load_env

    (tmp_path / ".env").write_bytes("\ufeffANTHROPIC_API_KEY=가짜\n".encode("utf-8"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert _load_env(tmp_path) is not None
    import os
    assert os.environ["ANTHROPIC_API_KEY"] == "가짜", "BOM 이 이름에 붙어 있다"


def test_이미_있는_환경변수는_덮어쓰지_않는다(tmp_path, monkeypatch):
    """배포 환경변수가 파일보다 세야 한다. 안 그러면 배포가 조용히 개발 키를 쓴다."""
    from prefab.__main__ import _load_env
    import os

    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=파일값\n")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "환경값")
    _load_env(tmp_path)
    assert os.environ["ANTHROPIC_API_KEY"] == "환경값"


def test_상위_폴더까지_올라가며_찾는다(tmp_path, monkeypatch):
    """apps/api 에서 돌리든 저장소 루트에서 돌리든 같게 동작해야 한다."""
    from prefab.__main__ import _load_env
    import os

    (tmp_path / ".env").write_text("PREFAB_TEST_ONLY=1\n")
    deep = tmp_path / "apps" / "api"
    deep.mkdir(parents=True)
    monkeypatch.delenv("PREFAB_TEST_ONLY", raising=False)
    assert _load_env(deep) == str(tmp_path / ".env")
    assert os.environ["PREFAB_TEST_ONLY"] == "1"


def test_env가_없어도_죽지_않는다(tmp_path):
    from prefab.__main__ import _load_env

    assert _load_env(tmp_path) is None
