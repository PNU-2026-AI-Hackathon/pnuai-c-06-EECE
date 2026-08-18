"""검사 결과 → API_CONTRACT.md 응답 dict.

pipeline 이 이 파일의 핵심이다. 못 한 단계를 사유와 함께 그대로 싣는다.
"""

from __future__ import annotations

from typing import Any

from . import catalog
from .bom import Bom
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
    # 해제된 발견은 심각도로 세지 않는다. 데이터시트로 풀린 항목이 화면에
    # "심각 1건" 으로도 남으면 해제가 일어난 것처럼 보이지 않는다.
    # 이렇게 해야 critical + warning + cleared 가 발견 개수와 항상 같다.
    open_findings = [f for f in findings if f.verdict is not Verdict.PASS]
    return {
        "critical": sum(1 for f in open_findings if f.severity is Severity.CRITICAL),
        "warning": sum(1 for f in open_findings if f.severity is Severity.WARNING),
        "cleared": sum(1 for f in findings if f.verdict is Verdict.PASS),
        "rules_run": len(engine.ran),
        "rules_skipped": len(engine.skipped),
        # 계약 확장: 카탈로그 전체 개수. run + skipped 와 항상 같다.
        "rules_total": catalog.TOTAL,
        "parts_identified": parts_identified,
        "parts_total": netlist.part_count,
    }


def _identify_step(has_bom: bool, pinmap, bom=None, refs=None) -> tuple[str, str]:
    """2단계 — 부품 식별. 무엇까지 알아냈는지 정확히 적는다."""
    if bom is not None:
        m = bom.match(refs or set())
        # 넷리스트에 있는데 BOM 에 없거나, 있어도 부품번호가 빈 행 — 둘 다 "모르는 것"이다
        unknown = list(m.missing_in_bom) + list(m.blank_mpn)
        total = len(m.identified) + len(unknown)
        detail = f"BOM {len(bom)}행 · 부품번호 확인 {len(m.identified)}/{total}"
        if unknown:
            detail += f" · 미식별 {', '.join(sorted(unknown)[:5])}"
        for note in bom.parse_notes():
            detail += f" · {note}"
        return ("done" if not unknown else "partial"), detail
    if has_bom:
        return "done", "BOM 으로 부품번호 확인"
    if pinmap:
        modules = " · ".join(f"{ref}={mid}" for ref, mid in sorted(pinmap.modules_matched.items()))
        return (
            "partial",
            f"BOM 없음 · 좌표로 모듈 핀아웃만 확정 ({modules} · 패드 {len(pinmap)}개)",
        )
    return "partial", "BOM 없음 · 좌표 클러스터링으로 전원 도메인만 추정"


def _firmware_step(firmware, pinmap) -> tuple[str, str]:
    """3단계 — 펌웨어 정적 분석. 못 짚은 핀이 있으면 숨기지 않는다."""
    if firmware is None:
        return "skipped", "펌웨어 미제출"

    mapped = [p for p in firmware.pins if pinmap.find(silk=p.silk, gpio=p.gpio) is not None]
    unmapped = len(firmware.pins) - len(mapped)

    detail = (
        f"소스 {len(firmware.files)}개 · {firmware.total_lines}줄 · "
        f"코드가 쓰는 핀 {len(firmware.pins)}개 "
        f"({' · '.join(firmware.labels) or '없음'})"
    )
    if unmapped:
        detail += f" · 회로도에서 못 짚은 핀 {unmapped}개"
    if firmware.unresolved:
        detail += f" · 못 읽은 자리 {len(firmware.unresolved)}곳 ({firmware.unresolved_summary})"

    status = "done" if firmware.pins and not unmapped and not firmware.unresolved else "partial"
    return status, detail


def build_pipeline(
    netlist: Netlist,
    engine: EngineResult,
    has_bom: bool,
    firmware,
    pinmap,
    bom=None,
) -> list[dict[str, Any]]:
    step = dict(PIPELINE_NAMES)

    identify = _identify_step(has_bom, pinmap, bom, set(netlist.parts))
    firmware_step = _firmware_step(firmware, pinmap)

    # 부품번호를 알면 무엇을 조회할 대상인지까지 말한다. 아직 조회는 못 한다
    if bom is not None and bom.mpns:
        mpns = " · ".join(sorted(bom.mpns)[:3])
        datasheet = ("skipped", f"데이터시트 파이프라인 미구현 — 조회 대상 {mpns}")
    elif has_bom:
        datasheet = ("skipped", "데이터시트 파이프라인 미구현")
    else:
        datasheet = ("skipped", "BOM 없음 · 부품번호를 알 수 없음")

    engine_detail = (
        f"{catalog.TOTAL}개 중 {len(engine.ran)}개 실행 · "
        f"미구현 {len(engine.skipped_not_implemented)} · "
        f"입력 부족 {len(engine.skipped_missing_input)}"
    )

    parse_detail = f"네트 {netlist.net_count} · 부품 {netlist.part_count}"
    # 읽으며 뺀 줄이 있으면 그대로 붙인다. 조용히 버리지 않는다 (CLAUDE.md 2-4).
    notes = netlist.parse_notes()
    if notes:
        parse_detail += " · " + " · ".join(notes)

    return [
        {"step": 1, "name": step[1], "status": "done", "detail": parse_detail},
        {"step": 2, "name": step[2], "status": identify[0], "detail": identify[1]},
        {"step": 3, "name": step[3], "status": firmware_step[0], "detail": firmware_step[1]},
        {"step": 4, "name": step[4], "status": datasheet[0], "detail": datasheet[1]},
        {"step": 5, "name": step[5], "status": "skipped", "detail": "데이터시트 없음"},
        {"step": 6, "name": step[6], "status": "done", "detail": engine_detail},
        {"step": 7, "name": step[7], "status": "done", "detail": None},
    ]


def build_result(
    *,
    check_id: str,
    created_at: str,
    analysis,
    netlist_filename: str,
    bom_filename: str | None = None,
    firmware_filename: str | None = None,
    parts_identified: int = 0,
    bom: "Bom | None" = None,
) -> dict[str, Any]:
    netlist = analysis.netlist
    engine = analysis.engine
    pinmap = analysis.graph.pinmap
    firmware = analysis.firmware
    bom = analysis.bom
    has_bom = bom_filename is not None or bom is not None

    firmware_input: dict[str, Any] | None = None
    if firmware_filename is not None:
        firmware_input = {"filename": firmware_filename}
        if firmware is not None:
            firmware_input["files"] = len(firmware.files)

    bom_detail: str | None = None
    if bom is not None:
        m = bom.match(list(netlist.parts))
        parts_identified = m.identified_count
        bits = [f"부품 {m.identified_count}/{netlist.part_count} 식별",
                f"미식별 {len(m.missing_in_bom) + len(m.blank_mpn)}"]
        if m.missing_in_bom:
            bits.append("BOM 에 행 없음: " + ", ".join(m.missing_in_bom[:6]))
        if m.blank_mpn:
            bits.append("부품번호 빈 칸: " + ", ".join(m.blank_mpn[:6]))
        # BOM 에만 있는 부품은 BOM 과 회로도가 어긋났다는 뜻이다. 그냥 넘기지 않는다.
        if m.extra_in_bom:
            bits.append("⚠ 회로도에 없는 BOM 부품: " + ", ".join(m.extra_in_bom[:6]))
        bits.extend(bom.parse_notes())
        bom_detail = " · ".join(bits)

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
            "bom": (
                {"filename": bom_filename or (bom.filename if bom else ""), "parts": len(bom) if bom else 0}
                if has_bom
                else None
            ),
            "firmware": firmware_input,
        },
        "summary": build_summary(netlist, engine, parts_identified or analysis.parts_identified),
        "pipeline": build_pipeline(netlist, engine, has_bom, firmware, pinmap, analysis.bom),
        "findings": [f.to_dict() for f in engine.findings],
        "netlist": analysis.to_netlist_dict(),
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
