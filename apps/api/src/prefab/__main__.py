"""python -m prefab <넷리스트> [--json]

프론트의 목 데이터를 다시 뽑는 명령이기도 하다 (요청서 3번):

    python -m prefab tests/fixtures/esp32-c6-presence-smart-light.d356 --json > check.json
    python -m prefab --rules-json > rules.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .netlist.d356 import NetlistParseError
from .report import build_result, build_rules_catalog
from .runner import analyze

#: 목 데이터를 재생성해도 diff 가 나지 않도록 CLI 는 시각을 고정한다.
FIXED_CREATED_AT = "2026-08-17T04:20:00Z"
FIXED_CHECK_ID = "chk_sample01"


def _human(analysis, path: Path) -> str:
    out: list[str] = []
    bar = "=" * 74
    out.append(bar)
    out.append(f"PREFAB — {path.name}")
    out.append(bar)
    out.append(f"네트 {analysis.netlist.net_count} · 부품 {analysis.netlist.part_count}")
    out.append("")
    out.append("전원 도메인 추론")
    for ref, dom in analysis.graph.domains().items():
        volts = f"{dom.volts}V" if dom.known else "모름"
        out.append(f"  {ref:<5} {volts:<7} [{dom.confidence:<8}] {dom.basis}")
    out.append("")
    out.append(bar)
    out.append("발견")
    out.append(bar)
    if not analysis.engine.findings:
        out.append("  없음")
    for f in analysis.engine.findings:
        out.append("")
        out.append(f"[{f.severity.value}] {f.rule}  net: {f.net}")
        out.append(f"       {f.claim}")
        for ev in f.evidence:
            for line in (ev.text or "").splitlines():
                out.append(f"         {line}")
        if f.unresolved_reason:
            out.append(f"       ! {f.unresolved_reason}")
    out.append("")
    out.append(bar)
    e = analysis.engine
    out.append(
        f"{len(e.findings)}건 · 규칙 {e.total}개 중 {len(e.ran)}개 실행 "
        f"(미구현 {len(e.skipped_not_implemented)} · 입력 부족 {len(e.skipped_missing_input)})"
    )
    out.append(bar)
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="prefab", description="회로도와 펌웨어의 어긋남을 찾습니다.")
    ap.add_argument("netlist", nargs="?", help="IPC-D-356 파일")
    ap.add_argument("--json", action="store_true", help="API 계약과 같은 JSON 으로 출력")
    ap.add_argument("--rules-json", action="store_true", help="규칙 카탈로그 JSON 만 출력")
    args = ap.parse_args(argv)

    if args.rules_json:
        print(json.dumps(build_rules_catalog(), ensure_ascii=False, indent=2))
        return 0

    if not args.netlist:
        ap.error("넷리스트 파일이 필요합니다.")

    path = Path(args.netlist)
    if not path.exists():
        print(f"파일을 찾지 못했습니다: {path}", file=sys.stderr)
        return 2

    try:
        analysis = analyze(path.read_text(encoding="utf-8", errors="replace"), filename=path.name)
    except NetlistParseError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        result = build_result(
            check_id=FIXED_CHECK_ID,
            created_at=FIXED_CREATED_AT,
            netlist=analysis.netlist,
            engine=analysis.engine,
            netlist_filename=path.name,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_human(analysis, path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
