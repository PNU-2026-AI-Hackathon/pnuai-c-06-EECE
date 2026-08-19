"""부품 사실 DB — 사실 모델과 캐시.

여기서 지키려는 것은 하나다. **출처 없는 값이 판정에 쓰이지 않는 것.**
틀린 사실 하나는 그 부품을 쓰는 모든 사용자에게 오탐을 만든다 (CLAUDE.md 2-3).
"""

from __future__ import annotations

import pytest

from prefab.datasheet.facts import (
    CONF_HIGH,
    CONF_LOW,
    CONF_NONE,
    OUTPUT_TYPE,
    TIER_OFFICIAL,
    VCC_NOMINAL,
    VIH_MIN,
    VIL_MAX,
    VIN_ABSOLUTE_MAX,
    VOH_MAX,
    Fact,
    FactSet,
)
from prefab.datasheet.store import FactStore


@pytest.fixture
def store(tmp_path):
    return FactStore(tmp_path / "t.db")


def _fact(**kw) -> Fact:
    base = dict(
        mpn="HLK-LD2410C",
        field=VOH_MAX,
        value=3.3,
        unit="V",
        table="Electrical Characteristics",
        page=3,
        quote="OUT high level output voltage 3.3V",
        confidence=CONF_HIGH,
    )
    return Fact(**{**base, **kw})


# ── 사실 하나가 판정에 쓸 수 있는가 ──────────────────────────────────


def test_출처와_확신도가_다_있어야_판정에_쓴다():
    assert _fact().usable


@pytest.mark.parametrize(
    "kw, 왜",
    [
        ({"page": None}, "몇 쪽에서 읽었는지 모른다"),
        ({"quote": None}, "원문 인용이 없다"),
        ({"confidence": CONF_LOW}, "확신이 낮은 값으로 PASS 를 내지 않는다"),
        ({"value": None, "reason": "명시 없음"}, "값 자체가 없다"),
    ],
)
def test_하나라도_빠지면_판정에_못_쓴다(kw, 왜):
    assert not _fact(**kw).usable, 왜


def test_값이_없어도_사실은_사실이다():
    """찾아봤지만 없더라 — 실패가 아니라 정상적인 결과다."""
    f = _fact(field=OUTPUT_TYPE, value=None, page=None, quote=None,
              confidence=CONF_NONE, reason="push-pull 인지 open-drain 인지 명시 없음")
    assert not f.usable
    assert f.reason  # 왜 모르는지는 말할 수 있어야 한다


# ── FactSet — 규칙이 보는 유일한 창구 ────────────────────────────────


def test_판정_가능한_것만_usable_로_나온다():
    s = FactSet([_fact(), _fact(field=VIH_MIN, value=2.0, page=None, quote=None)])
    assert s.usable("HLK-LD2410C", VOH_MAX) is not None
    assert s.usable("HLK-LD2410C", VIH_MIN) is None, "출처 없는 값이 새어 나갔다"
    assert s.get("HLK-LD2410C", VIH_MIN) is not None, "기록 자체는 남아 있어야 한다"


def test_모르는_부품은_조용히_None():
    s = FactSet([_fact()])
    assert s.usable("없는부품", VOH_MAX) is None
    assert s.facts_of("없는부품") == []


# ── 저장 — 스킬 5단계 스키마 강제 ────────────────────────────────────


def test_스킬_예시_그대로_저장된다(store):
    r = store.save(
        {
            "mpn": "HLK-LD2410C",
            "facts": [
                {"field": VOH_MAX, "value": 3.3, "unit": "V",
                 "table": "Electrical Characteristics", "page": 3,
                 "quote": "OUT high level output voltage 3.3V", "confidence": CONF_HIGH},
                {"field": VCC_NOMINAL, "value": 5.0, "unit": "V",
                 "table": "Recommended Operating Conditions", "page": 2,
                 "quote": "Supply voltage 5V DC", "confidence": CONF_HIGH},
                {"field": OUTPUT_TYPE, "value": None, "confidence": CONF_NONE,
                 "reason": "데이터시트에 명시되지 않음"},
            ],
            "source_url": "https://example.invalid/ld2410c.pdf",
            "source_tier": TIER_OFFICIAL,
        }
    )
    assert (r.stored, r.negative, r.rejected) == (2, 1, [])
    assert store.size() == (1, 3)


def test_출처_없는_값은_DB에_안_들어간다(store):
    r = store.save({"mpn": "X", "facts": [
        {"field": VOH_MAX, "value": 3.3, "confidence": CONF_HIGH},
    ]})
    assert r.stored == 0
    assert store.size() == (0, 0)
    assert "출처" in r.rejected[0].why


def test_이유_없는_모름도_안_들어간다(store):
    """'모른다'고만 하고 왜 모르는지 안 말하는 건 사실이 아니다 (CLAUDE.md 2-2)."""
    r = store.save({"mpn": "X", "facts": [
        {"field": VIL_MAX, "value": None, "confidence": CONF_NONE},
    ]})
    assert r.stored == r.negative == 0
    assert not r.ok


def test_거절해도_나머지는_저장된다(store):
    r = store.save({"mpn": "X", "facts": [
        {"field": VOH_MAX, "value": 3.3, "table": "EC", "page": 1,
         "quote": "q", "confidence": CONF_HIGH},
        {"field": VIH_MIN, "value": 2.0, "confidence": CONF_HIGH},
    ]})
    assert r.stored == 1 and len(r.rejected) == 1


def test_mpn이_없으면_통째로_거절(store):
    assert not store.save({"mpn": "  ", "facts": []}).ok


# ── 조회 — 1단계 캐시 ───────────────────────────────────────────────


def test_적중과_미적중을_구분해서_보고한다(store):
    store.save({"mpn": "A", "facts": [
        {"field": VOH_MAX, "value": 3.3, "table": "EC", "page": 1,
         "quote": "q", "confidence": CONF_HIGH}]})

    lk = store.lookup(["A", "B", "A", ""])
    assert lk.hits == ["A"]
    assert lk.misses == ["B"], "미적중이 곧 LLM 을 불러야 할 목록이다"
    assert lk.hit_rate == 0.5


def test_빈_목록은_DB를_두드리지_않는다(store):
    lk = store.lookup([])
    assert len(lk.facts) == 0 and lk.hit_rate == 0.0


def test_같은_부품을_다시_읽으면_덮어쓴다(store):
    for page in (1, 7):
        store.save({"mpn": "A", "facts": [
            {"field": VOH_MAX, "value": 3.3, "table": "EC", "page": page,
             "quote": "q", "confidence": CONF_HIGH}]})
    assert store.size() == (1, 1), "같은 (부품,항목)이 두 줄로 쌓이면 안 된다"
    assert store.lookup(["A"]).facts.get("A", VOH_MAX).page == 7


def test_문자열_값도_왕복한다(store):
    """output_type 처럼 숫자가 아닌 사실도 있다."""
    store.save({"mpn": "A", "facts": [
        {"field": OUTPUT_TYPE, "value": "push-pull", "table": "EC", "page": 4,
         "quote": "Output stage: push-pull", "confidence": CONF_HIGH}]})
    f = store.lookup(["A"]).facts.usable("A", OUTPUT_TYPE)
    assert f.value == "push-pull"


def test_출처가_인용문까지_왕복한다(store):
    """화면이 'p.3 Electrical Characteristics' 를 보여줄 수 있어야 한다."""
    store.save({"mpn": "A", "facts": [
        {"field": VOH_MAX, "value": 3.3, "table": "Electrical Characteristics",
         "page": 3, "quote": "OUT high 3.3V", "confidence": CONF_HIGH}],
        "source_url": "https://example.invalid/a.pdf", "source_tier": TIER_OFFICIAL})
    f = store.lookup(["A"]).facts.get("A", VOH_MAX)
    assert f.cite() == "Electrical Characteristics · p.3"
    assert f.quote == "OUT high 3.3V"
    assert f.source_tier == TIER_OFFICIAL


# ── 러너 연결 — BOM 부품번호로 캐시를 두드린다 ────────────────────────


def _analyze(**kw):
    from prefab.runner import analyze
    from tests._builder import board, rec

    text = board(
        rec("+3V3", "U1", "3V3", x=0.0, y=0.0),
        rec("+3V3", "U3", "VCC", x=0.5, y=0.0),
    )
    return analyze(text, **kw)


def test_사실_DB를_안_주면_아무_일도_안_일어난다():
    a = _analyze()
    assert a.facts is None
    assert "datasheet" not in a.context.available()


def test_BOM_부품번호로_사실을_찾아_규칙에_넘긴다(store):
    store.save({"mpn": "ESP32-C6-WROOM-1", "facts": [
        {"field": VOH_MAX, "value": 3.3, "unit": "V", "table": "EC", "page": 3,
         "quote": "VOH 3.3V", "confidence": CONF_HIGH}]})

    a = _analyze(
        bom_bytes=b"Reference,MPN\nU1,ESP32-C6-WROOM-1\nU3,HLK-LD2410C\n",
        fact_store=store,
    )
    assert a.facts.hits == ["ESP32-C6-WROOM-1"]
    assert a.facts.misses == ["HLK-LD2410C"], "아직 안 읽은 부품을 정직하게 남긴다"
    assert "datasheet" in a.context.available()


def test_아는_게_없으면_데이터시트가_있는_척하지_않는다(store):
    """빈 FactSet 을 넘기면 엔진이 '데이터시트가 있다'고 착각한다."""
    a = _analyze(bom_bytes="Reference,MPN\nU1,모르는부품\n".encode(), fact_store=store)
    assert a.facts.misses == ["모르는부품"]
    assert "datasheet" not in a.context.available()


def test_BOM이_없으면_조회하지_않는다(store):
    assert _analyze(fact_store=store).facts is None


def test_같은_부품번호가_여러_행에_있어도_한_번만_조회한다():
    from prefab.bom import parse_text
    b = parse_text("Reference,MPN\nC1,GRM155R\nC2,GRM155R\nR1,\n")
    assert b.mpns == ["GRM155R"]


# ── CLI — API 키 없이 손으로 채우는 길 ──────────────────────────────


def _run(argv, capsys):
    from prefab.__main__ import main

    code = main(argv)
    return code, capsys.readouterr()


def test_손으로_적은_사실_파일이_DB에_들어간다(tmp_path, capsys):
    f = tmp_path / "a.json"
    f.write_text(
        '{"mpn":"A","source_tier":"official","facts":[{"field":"voh_max",'
        '"value":3.3,"unit":"V","table":"EC","page":3,"quote":"VOH 3.3V",'
        '"confidence":"high"}]}',
        encoding="utf-8",
    )
    db = tmp_path / "t.db"
    code, out = _run(["--facts-load", str(f), "--db", str(db)], capsys)
    assert code == 0
    assert "부품 DB: 0 → 1" in out.out
    assert FactStore(db).lookup(["A"]).facts.usable("A", VOH_MAX) is not None


def test_거절되면_0이_아닌_코드로_끝난다(tmp_path, capsys):
    """조용히 성공한 척하지 않는다 (CLAUDE.md 2-4)."""
    f = tmp_path / "a.json"
    f.write_text('{"mpn":"A","facts":[{"field":"voh_max","value":3.3}]}', encoding="utf-8")
    code, out = _run(["--facts-load", str(f), "--db", str(tmp_path / "t.db")], capsys)
    assert code == 1
    assert "출처" in out.err


def test_서식을_그대로_넣으면_통째로_거절된다(tmp_path, capsys):
    """실수로 서식을 넣어도 DB 가 더러워지지 않아야 한다."""
    from pathlib import Path as P

    db = tmp_path / "t.db"
    code, _ = _run(["--facts-load", str(P("parts/_TEMPLATE.json")), "--db", str(db)], capsys)
    assert code == 1
    assert FactStore(db).size() == (0, 0)


def test_깨진_JSON은_죽지_않고_보고한다(tmp_path, capsys):
    f = tmp_path / "a.json"
    f.write_text("{ 이건 JSON 이 아니다", encoding="utf-8")
    code, out = _run(["--facts-load", str(f), "--db", str(tmp_path / "t.db")], capsys)
    assert code == 1 and "JSON" in out.err


def test_없는_파일도_죽지_않는다(tmp_path, capsys):
    code, out = _run(["--facts-load", str(tmp_path / "없다.json"), "--db", str(tmp_path / "t.db")], capsys)
    assert code == 1 and "찾지 못했" in out.err


# ── 보드 → 칩 ──────────────────────────────────────────────────────


def test_보드_이름으로_물어도_칩의_핀_특성이_나온다(store):
    """BOM 에는 보드 이름이 적히고 데이터시트는 칩 이름으로 나온다.
    `prefab-datasheet` 스킬이 경고하는 "모듈 vs 칩" 함정이다."""
    store.save({
        "mpn": "ESP32-C6",
        "applies_to_boards": ["XIAO-ESP32C6"],
        "source_tier": TIER_OFFICIAL,
        "facts": [{"field": VIN_ABSOLUTE_MAX, "value": 3.6, "unit": "V",
                   "table": "Table 5-1", "page": 64, "quote": "3.6 V",
                   "confidence": CONF_HIGH}],
    })
    lk = store.lookup(["XIAO-ESP32C6"])
    assert lk.hits == ["XIAO-ESP32C6"]
    assert lk.facts.usable("XIAO-ESP32C6", VIN_ABSOLUTE_MAX).value == 3.6


def test_공급_전압은_물려받지_않는다(store):
    """보드에는 레귤레이터가 있다. XIAO ESP32C6 은 USB 5V 를 받아
    칩에 3.3V 를 준다. 칩의 3.3V 를 보드 공급 전압이라고 하면 틀린 값이다."""
    store.save({
        "mpn": "ESP32-C6",
        "applies_to_boards": ["XIAO-ESP32C6"],
        "source_tier": TIER_OFFICIAL,
        "facts": [{"field": VCC_NOMINAL, "value": 3.3, "unit": "V", "table": "T",
                   "page": 64, "quote": "3.3", "confidence": CONF_HIGH}],
    })
    assert store.lookup(["XIAO-ESP32C6"]).facts.get("XIAO-ESP32C6", VCC_NOMINAL) is None
    assert store.lookup(["ESP32-C6"]).facts.usable("ESP32-C6", VCC_NOMINAL).value == 3.3


def test_보드가_직접_가진_사실이_더_세다(store):
    """보드 데이터시트에 값이 있으면 그게 맞다. 칩 값이 덮으면 안 된다."""
    store.save({"mpn": "ESP32-C6", "applies_to_boards": ["XIAO-ESP32C6"],
                "source_tier": TIER_OFFICIAL, "facts": [
        {"field": VIN_ABSOLUTE_MAX, "value": 3.6, "table": "T", "page": 64,
         "quote": "칩", "confidence": CONF_HIGH}]})
    store.save({"mpn": "XIAO-ESP32C6", "source_tier": TIER_OFFICIAL, "facts": [
        {"field": VIN_ABSOLUTE_MAX, "value": 5.0, "table": "T", "page": 1,
         "quote": "보드", "confidence": CONF_HIGH}]})
    f = store.lookup(["XIAO-ESP32C6"]).facts.usable("XIAO-ESP32C6", VIN_ABSOLUTE_MAX)
    assert f.value == 5.0 and f.quote == "보드"


def test_물려받은_사실은_어느_칩에서_왔는지_말한다(store):
    """화면에 '3.6V' 만 뜨면 사용자는 이게 보드 규격인 줄 안다."""
    store.save({"mpn": "ESP32-C6", "applies_to_boards": ["XIAO-ESP32C6"],
                "source_tier": TIER_OFFICIAL, "facts": [
        {"field": VIN_ABSOLUTE_MAX, "value": 3.6, "table": "T", "page": 64,
         "quote": "q", "confidence": CONF_HIGH}]})
    f = store.lookup(["XIAO-ESP32C6"]).facts.get("XIAO-ESP32C6", VIN_ABSOLUTE_MAX)
    assert "ESP32-C6 칩의 핀 특성" in f.reason
    assert f.page == 64, "출처는 칩 데이터시트 그대로여야 한다"


def test_별칭이_없으면_아무_일도_안_일어난다(store):
    store.save({"mpn": "ESP32-C6", "source_tier": TIER_OFFICIAL, "facts": [
        {"field": VIN_ABSOLUTE_MAX, "value": 3.6, "table": "T", "page": 64,
         "quote": "q", "confidence": CONF_HIGH}]})
    assert store.lookup(["XIAO-ESP32C6"]).misses == ["XIAO-ESP32C6"]
