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
    # 이렇게 해야 critical + warning + info + cleared 가 발견 개수와 항상 같다.
    open_findings = [f for f in findings if f.verdict is not Verdict.PASS]
    return {
        "critical": sum(1 for f in open_findings if f.severity is Severity.CRITICAL),
        "warning": sum(1 for f in open_findings if f.severity is Severity.WARNING),
        # INFO 를 안 세면 "발견 3건" 인데 타일 합이 2 가 된다. 심각도는 세 단계다.
        "info": sum(1 for f in open_findings if f.severity is Severity.INFO),
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
        # **어떻게 풀었는지를 말한다.** 모듈은 좌표(헤더 열 정렬)로, 맨칩은 핀 이름으로
        # 푼다. 둘을 뭉뚱그리면 사용자가 무엇을 더 주면 나아지는지 알 수 없다.
        modules = " · ".join(f"{ref}={mid}" for ref, mid in sorted(pinmap.modules_matched.items()))
        how = f"좌표로 모듈 핀아웃 확정 ({modules})" if modules else "핀 이름으로 GPIO 확정"
        return "partial", f"BOM 없음 · {how} · 패드 {len(pinmap)}개"
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
    facts=None,
) -> list[dict[str, Any]]:
    step = dict(PIPELINE_NAMES)

    identify = _identify_step(has_bom, pinmap, bom, set(netlist.parts))
    firmware_step = _firmware_step(firmware, pinmap)

    datasheet, extract = _datasheet_steps(has_bom, bom, facts, engine)

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
        {"step": 5, "name": step[5], "status": extract[0], "detail": extract[1]},
        {"step": 6, "name": step[6], "status": "done", "detail": engine_detail},
        {"step": 7, "name": step[7], "status": "done", "detail": None},
    ]


def _datasheet_steps(has_bom, bom, facts, engine) -> tuple[tuple[str, str], tuple[str, str]]:
    """4·5 단계 — 데이터시트를 얼마나 읽었나.

    **한 일을 안 했다고 적지 않는다.** 사실을 실제로 읽어서 판정에 썼는데도
    "미구현" 이라고 적으면 4-2 와 똑같은 종류의 거짓말이다 (CLAUDE.md 2-4).
    반대로 하나 읽었다고 `done` 이라고 하지도 않는다. 못 읽은 부품을 그대로 센다.
    """
    if not has_bom or bom is None or not bom.mpns:
        return (
            ("skipped", "BOM 없음 · 부품번호를 알 수 없음"),
            ("skipped", "조회할 부품번호가 없음"),
        )

    total = len(bom.mpns)
    if facts is None or not facts.hits:
        missing = " · ".join(sorted(bom.mpns)[:3])
        return (
            ("skipped", f"부품 {total}개 중 0개 수집 — 조회 대상 {missing}"),
            ("skipped", "읽어 둔 사실 없음"),
        )

    hits = len(facts.hits)
    collect = [f"부품 {total}개 중 {hits}개 수집"]
    if facts.misses:
        collect.append("미수집: " + " · ".join(sorted(facts.misses)[:6]))
    # 전부 모으기 전에는 done 이 아니다. 부분 수집을 완료라고 적지 않는다.
    collect_status = "done" if not facts.misses else "partial"

    used = sum(1 for f in engine.findings if any(e.kind == "datasheet" for e in f.evidence))
    bits = [f"사실 {len(facts.facts)}건 확보"]
    if used:
        bits.append(f"판정 {used}건에 근거로 사용")
    else:
        bits.append("아직 어떤 판정에도 쓰이지 않음")
    return ((collect_status, " · ".join(collect)), ("done", " · ".join(bits)))


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
                # Bom 에는 파일명이 없다. 파일명은 업로드가 알고 규칙은 모른다.
                # 예전 구현의 잔재로 bom.filename 을 읽고 있었다 — 호출자가
                # bom_filename 을 안 주면 AttributeError 로 터졌다.
                {"filename": bom_filename or "", "parts": len(bom) if bom else 0}
                if has_bom
                else None
            ),
            "firmware": firmware_input,
        },
        "summary": build_summary(netlist, engine, parts_identified or analysis.parts_identified),
        "pipeline": build_pipeline(
            netlist, engine, has_bom, firmware, pinmap, analysis.bom, analysis.facts
        ),
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
