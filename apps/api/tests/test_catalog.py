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
    payload = build_rules_catalog()["rules"]
    assert len(payload) == catalog.TOTAL
    assert any(r["implemented"] is False for r in payload)
    assert {r["id"] for r in payload if r["implemented"]} == set(rules.IMPLEMENTED_IDS)


def test_catalog_total_is_eleven():
    assert catalog.TOTAL == 11
