"""검사 결과 → API_CONTRACT.md 응답 dict.

pipeline 이 이 파일의 핵심이다. 못 한 단계를 사유와 함께 그대로 싣는다.
"""

from __future__ import annotations

from typing import Any

from . import catalog
from .engine import EngineResult
from .netlist.d356 import Netlist
from .types import Severity, Verdict

PIPELINE_NAMES = (
    (1, "넷리스트 파싱"),
    (2, "부품 식별"),
    (3, "펌웨어 정적 분석"),
    (4, "데이터시트 수집"),
    (5, "전기적 사실 추출"),
    (6, "규칙 엔진"),
    (7, "리포트 생성"),
)


def build_summary(netlist: Netlist, engine: EngineResult, parts_identified: int = 0) -> dict[str, Any]:
    findings = engine.findings
    return {
        "critical": sum(1 for f in findings if f.severity is Severity.CRITICAL),
        "warning": sum(1 for f in findings if f.severity is Severity.WARNING),
        "cleared": sum(1 for f in findings if f.verdict is Verdict.PASS),
        "rules_run": len(engine.ran),
        "rules_skipped": len(engine.skipped),
        # 계약 확장: 카탈로그 전체 개수. run + skipped 와 항상 같다.
        "rules_total": catalog.TOTAL,
        "parts_identified": parts_identified,
        "parts_total": netlist.part_count,
    }


def build_pipeline(
    netlist: Netlist,
    engine: EngineResult,
    has_bom: bool,
    has_firmware: bool,
) -> list[dict[str, Any]]:
    step = dict(PIPELINE_NAMES)

    parse_detail = f"네트 {netlist.net_count} · 부품 {netlist.part_count}"

    if has_bom:
        identify = ("done", "BOM 으로 부품번호 확인")
    else:
        identify = ("partial", "BOM 없음 · 좌표 클러스터링으로 전원 도메인만 추정")

    if has_firmware:
        firmware = ("skipped", "펌웨어 정적 분석기 미구현 — 파일은 받았습니다")
    else:
        firmware = ("skipped", "펌웨어 미제출")

    if has_bom:
        datasheet = ("skipped", "데이터시트 파이프라인 미구현")
    else:
        datasheet = ("skipped", "BOM 없음 · 부품번호를 알 수 없음")

    facts = ("skipped", "데이터시트 없음")

    engine_detail = (
        f"{catalog.TOTAL}개 중 {len(engine.ran)}개 실행 · "
        f"미구현 {len(engine.skipped_not_implemented)} · "
        f"입력 부족 {len(engine.skipped_missing_input)}"
    )

    return [
        {"step": 1, "name": step[1], "status": "done", "detail": parse_detail},
        {"step": 2, "name": step[2], "status": identify[0], "detail": identify[1]},
        {"step": 3, "name": step[3], "status": firmware[0], "detail": firmware[1]},
        {"step": 4, "name": step[4], "status": datasheet[0], "detail": datasheet[1]},
        {"step": 5, "name": step[5], "status": facts[0], "detail": facts[1]},
        {"step": 6, "name": step[6], "status": "done", "detail": engine_detail},
        {"step": 7, "name": step[7], "status": "done", "detail": None},
    ]


def build_result(
    *,
    check_id: str,
    created_at: str,
    netlist: Netlist,
    engine: EngineResult,
    netlist_filename: str,
    bom_filename: str | None = None,
    firmware_filename: str | None = None,
    parts_identified: int = 0,
) -> dict[str, Any]:
    has_bom = bom_filename is not None
    has_firmware = firmware_filename is not None

    return {
        "check_id": check_id,
        "status": "done",
        "created_at": created_at,
        "inputs": {
            "netlist": {
                "filename": netlist_filename,
                "nets": netlist.net_count,
                "parts": netlist.part_count,
            },
            "bom": {"filename": bom_filename} if has_bom else None,
            "firmware": {"filename": firmware_filename} if has_firmware else None,
        },
        "summary": build_summary(netlist, engine, parts_identified),
        "pipeline": build_pipeline(netlist, engine, has_bom, has_firmware),
        "findings": [f.to_dict() for f in engine.findings],
        "netlist": netlist.to_dict(),
    }


def build_rules_catalog() -> dict[str, Any]:
    """GET /api/v1/rules. 미구현 규칙도 implemented:false 로 포함한다. 숨기지 않는다."""
    from . import rules as registry

    return {
        "rules": [
            {
                "id": spec.id,
                "title": spec.title,
                "tier": spec.tier,
                "severity": spec.severity.value,
                "needs": list(spec.needs),
                "implemented": registry.is_implemented(spec.id),
            }
            for spec in catalog.CATALOG
        ]
    }
