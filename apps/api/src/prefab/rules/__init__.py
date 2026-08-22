"""규칙 레지스트리.

여기에 모듈을 등록하면 그 규칙은 '구현됨'이다. 다른 곳에 플래그를 두지 않는다.
각 규칙 모듈은 RULE_ID, TITLE, SEVERITY, TIER, NEEDS, check(ctx) 를 노출한다.
"""

from __future__ import annotations

from types import ModuleType

from . import (
    r01_unusable_pin,
    r02_flash_pin_wired,
    r03_strapping_tied,
    r04_input_overvoltage,
    r05_unsupported_combo,
    r07_pin_not_connected,
    r08_connected_but_unused,
    r09_boot_output_load,
    r10_schematic_moved,
    r11_net_name_domain,
    r12_cross_domain,
    r14_pin_name_conflict,
    r15_output_below_vih,
    r16_init_order_glitch,
)

#: 실행 순서는 규칙 ID 순. 결과 정렬은 engine 이 따로 한다.
MODULES: tuple[ModuleType, ...] = (
    r01_unusable_pin,
    r02_flash_pin_wired,
    r03_strapping_tied,
    r04_input_overvoltage,
    r05_unsupported_combo,
    r07_pin_not_connected,
    r08_connected_but_unused,
    r09_boot_output_load,
    r10_schematic_moved,
    r11_net_name_domain,
    r12_cross_domain,
    r14_pin_name_conflict,
    r15_output_below_vih,
    r16_init_order_glitch,
)

BY_ID: dict[str, ModuleType] = {m.RULE_ID: m for m in MODULES}

IMPLEMENTED_IDS: frozenset[str] = frozenset(BY_ID)


def is_implemented(rule_id: str) -> bool:
    return rule_id in IMPLEMENTED_IDS
