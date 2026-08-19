"""카탈로그와 레지스트리가 어긋나지 않는지.

숫자가 세 군데 적혀 있어서 이미 한 번 어긋났다 (11 vs 12).
이 테스트가 그 재발을 막는다.
"""

from __future__ import annotations

from prefab import catalog, rules
from prefab.report import build_rules_catalog
from prefab.types import CONTRACT_NEEDS


def test_every_implemented_module_is_in_the_catalog():
    for rule_id in rules.IMPLEMENTED_IDS:
        assert rule_id in catalog.BY_ID, f"{rule_id} 가 카탈로그에 없다"


def test_module_metadata_matches_the_catalog():
    for rule_id, module in rules.BY_ID.items():
        spec = catalog.BY_ID[rule_id]
        assert module.TITLE == spec.title
        assert module.TIER == spec.tier
        assert module.SEVERITY == spec.severity
        assert tuple(module.NEEDS) == spec.needs


def test_needs_use_the_contract_vocabulary():
    for spec in catalog.CATALOG:
        for need in spec.needs:
            assert need in CONTRACT_NEEDS, f"{spec.id} 의 needs 에 계약에 없는 값: {need}"


def test_rule_ids_are_unique_and_zero_padded():
    ids = [s.id for s in catalog.CATALOG]
    assert len(ids) == len(set(ids))
    assert all(len(i) == 3 and i.startswith("R") for i in ids)


def test_r06_is_retired_and_not_reused():
    """R6(I2C 풀업 누락)은 Flux 가 이미 제공하므로 폐기했다. 번호를 재활용하지 않는다."""
    assert "R06" not in catalog.BY_ID


def test_unimplemented_rules_are_exposed_not_hidden():
    """구현 여부를 **모든 규칙에 대해** 내보낸다. 숨기지 않는다.

    원래 "미구현이 하나는 있다"를 함께 단정했는데, R10 이 들어오면서 11/11 이 되어
    그 단정이 깨졌다. 재기 좋은 상태를 전제로 삼은 것이었다 — 지키려던 것은
    **개수가 아니라 노출**이다. 카탈로그 전체가 실리고 레지스트리와 일치하면 된다.
    """
    payload = build_rules_catalog()["rules"]
    assert len(payload) == catalog.TOTAL
    assert all("implemented" in r for r in payload)
    assert {r["id"] for r in payload if r["implemented"]} == set(rules.IMPLEMENTED_IDS)


def test_catalog_total_is_eleven():
    assert catalog.TOTAL == 11


def test_proposed_rules_are_not_counted_in_the_catalog():
    """R13 은 하드웨어 담당 채택 판정 대기 중이다. rules_total 을 부풀리지 않는다."""
    proposed = {s.id for s in catalog.PROPOSED}
    assert proposed == {"R13"}
    assert not proposed & set(catalog.BY_ID)
    assert all(s.blocked_by for s in catalog.PROPOSED)


def test_differentiating_rules_are_now_implemented():
    """R07 · R08 이 돌기 시작했다. 차별 등급의 중심이다."""
    assert rules.is_implemented("R07")
    assert rules.is_implemented("R08")
    assert catalog.BY_ID["R07"].tier == "차별"
    assert catalog.BY_ID["R08"].tier == "차별"


def test_implemented_rules_declare_no_blocker():
    for spec in catalog.CATALOG:
        if rules.is_implemented(spec.id):
            assert spec.blocked_by is None, f"{spec.id} 는 구현됐는데 차단 사유가 남아 있다"


def test_요약의_심각도_합이_발견_개수와_같다():
    """심각도는 세 단계다. 하나라도 안 세면 화면의 타일 합이 발견 수보다 작아진다.

    `build_summary` 주석이 이 불변식을 못 박고 있는데, 지키는 테스트가
    R09 파일 안에 있었다. 규칙 하나에 매인 검사가 아니라 계약 불변식이라
    여기로 옮긴다 — R09 가 사라져도 이 규칙은 남아야 한다.
    """
    from pathlib import Path

    from prefab.report import build_result
    from prefab.runner import analyze

    fixtures = Path(__file__).parent / "fixtures"
    a = analyze(
        (fixtures / "esp32-c6-presence-smart-light.d356").read_text(),
        bom_bytes=(fixtures / "esp32-c6-presence-smart-light.bom.csv").read_bytes(),
    )
    r = build_result(check_id="c", created_at="t", analysis=a, netlist_filename="b.d356")
    s = r["summary"]

    assert s["critical"] + s["warning"] + s["info"] + s["cleared"] == len(r["findings"])
    assert s["rules_run"] + s["rules_skipped"] == s["rules_total"]
