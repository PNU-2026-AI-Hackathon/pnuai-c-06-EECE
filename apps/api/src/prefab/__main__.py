"""python -m prefab <넷리스트> [--json]

프론트의 목 데이터를 다시 뽑는 명령이기도 하다 (요청서 3번):

    python -m prefab tests/fixtures/esp32-c6-presence-smart-light.d356 --json > check.json
    python -m prefab --rules-json > rules.json

부품 사실 DB 는 **LLM 없이도** 손으로 채울 수 있다. 사람이 데이터시트를 읽고
`prefab-datasheet` 5단계 스키마로 적어서 넣으면 된다:

    python -m prefab --facts-load parts/hlk-ld2410c.json
    python -m prefab --facts

LLM 으로 PDF 에서 뽑을 수도 있다. 결과는 DB 가 아니라 **파일로 나온다** —
사람이 보고 커밋할지 정한 다음에 들어간다:

    python -m prefab --extract ld2410c.pdf --mpn HLK-LD2410C \
        --source-url https://... --source-tier official --pages 15-19 \
        > parts/hlk-ld2410c.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .bom import BomParseError
from .datasheet.store import FactStore
from .firmware import load_directory, load_zip
from .netlist.d356 import NetlistParseError
from .report import build_result, build_rules_catalog
from .types import Verdict
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
    if analysis.firmware:
        out.append("코드가 쓰는 핀")
        for u in analysis.firmware.pins:
            pad = analysis.graph.pinmap.find(silk=u.silk, gpio=u.gpio)
            where = f"{pad.silk} (GPIO{pad.gpio})" if pad else "회로도에서 못 찾음"
            out.append(f"  {u.label:<5} {u.direction:<8} {', '.join(u.symbols) or '—':<12} → {where}")
        out.append("")
    out.append(bar)
    out.append("발견")
    out.append(bar)
    if not analysis.engine.findings:
        out.append("  없음")
    for f in analysis.engine.findings:
        out.append("")
        # 판정이 PASS 인데 [CRITICAL] 로 찍으면 해제가 일어난 게 화면에 안 보인다.
        tag = "해제" if f.verdict is Verdict.PASS else f.severity.value
        out.append(f"[{tag}] {f.rule}  net: {f.net}")
        out.append(f"       {f.claim}")
        for ev in f.evidence:
            for line in (ev.text or "").splitlines():
                out.append(f"         {line}")
        if f.unresolved_reason:
            out.append(f"       ! {f.unresolved_reason}")
    out.append("")
    out.append(bar)
    e = analysis.engine
    cleared = sum(1 for f in e.findings if f.verdict is Verdict.PASS)
    if cleared:
        out.append(f"{len(e.findings)}건 중 {cleared}건은 데이터시트로 해제됐습니다.")
    out.append(
        f"{len(e.findings)}건 · 규칙 {e.total}개 중 {len(e.ran)}개 실행 "
        f"(미구현 {len(e.skipped_not_implemented)} · 입력 부족 {len(e.skipped_missing_input)})"
    )
    out.append(bar)
    return "\n".join(out)


def _extract(args) -> int:
    """PDF → LLM → 사실 JSON. **DB 에 바로 넣지 않는다.**

    사람이 파일을 보고 커밋할지 정하는 단계를 남긴다. 자동으로 DB 에 들어가면
    틀린 값이 언제 들어갔는지 아무도 모르게 된다.
    """
    from .datasheet.extract import ExtractionError, extract
    from .datasheet.pdf import PdfError, notes, read_pages

    try:
        import anthropic
    except ImportError:
        print("anthropic SDK 가 없습니다. `pip install anthropic` 하세요.", file=sys.stderr)
        return 2

    span = None
    if args.pages:
        try:
            lo, _, hi = args.pages.partition("-")
            span = range(int(lo), int(hi or lo) + 1)
        except ValueError:
            print(f"--pages 는 '15-19' 모양입니다: {args.pages}", file=sys.stderr)
            return 2

    try:
        pages = read_pages(args.extract, pages=span)
    except PdfError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    for note in notes(pages):
        print(note, file=sys.stderr)

    try:
        result = extract(
            anthropic.Anthropic(),
            mpn=args.mpn,
            pages=pages,
            source_url=args.source_url,
            source_tier=args.source_tier,
        )
    except ExtractionError as exc:
        print(f"추출하지 못했습니다 — {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # 네트워크·인증·속도제한 전부
        # SDK 는 자격증명이 없으면 요청을 만들 때 TypeError 를 던진다.
        # 트레이스백 대신 무엇이 없는지 말한다.
        if isinstance(exc, TypeError) and "authentication" in str(exc):
            print(
                "ANTHROPIC_API_KEY 가 없습니다. 키를 넣거나, LLM 없이 사람이 "
                "직접 채우려면 parts/README.md 를 보세요.",
                file=sys.stderr,
            )
        else:
            print(f"모델을 부르지 못했습니다 — {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    # 떨어뜨린 것은 화면에 남긴다. 조용히 버리지 않는다 (CLAUDE.md 2-4).
    for d in result.dropped:
        print(f"  버림  {d.field} — {d.why}", file=sys.stderr)
    print(
        f"사실 {len(result.facts)}건 · 버림 {len(result.dropped)}건 "
        f"(원문 대조 실패)", file=sys.stderr,
    )

    print(json.dumps(result.payload, ensure_ascii=False, indent=2))
    return 0


def _facts_load(paths: list[str], db: str) -> int:
    """사람이 적은 사실 파일을 DB 에 넣는다. **거절된 것을 전부 보여준다.**

    조용히 넣거나 조용히 버리면 무엇이 DB 에 있는지 아무도 모르게 된다 (CLAUDE.md 2-4).
    """
    store = FactStore(db)
    before = store.size()
    bad = 0

    for raw in paths:
        path = Path(raw)
        if not path.exists():
            print(f"파일을 찾지 못했습니다: {path}", file=sys.stderr)
            bad += 1
            continue
        try:
            report = store.save_json(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"{path.name}: JSON 을 읽지 못했습니다 — {exc}", file=sys.stderr)
            bad += 1
            continue

        print(f"{path.name}: 저장 {report.stored} · 값없음 기록 {report.negative} "
              f"· 거절 {len(report.rejected)}")
        for r in report.rejected:
            print(f"    거절  {r.mpn} {r.field} — {r.why}", file=sys.stderr)
            bad += 1

    parts, facts = store.size()
    print(f"부품 DB: {before[0]} → {parts} (사실 {before[1]} → {facts})")
    return 1 if bad else 0


def _facts_list(db: str) -> int:
    store = FactStore(db)
    parts, total = store.size()
    print(f"부품 {parts} · 사실 {total}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="prefab", description="회로도와 펌웨어의 어긋남을 찾습니다.")
    ap.add_argument("netlist", nargs="?", help="IPC-D-356 파일")
    ap.add_argument("--bom", help="부품 목록 CSV")
    ap.add_argument("--firmware", help="펌웨어 소스 디렉터리 또는 zip")
    ap.add_argument("--json", action="store_true", help="API 계약과 같은 JSON 으로 출력")
    ap.add_argument("--rules-json", action="store_true", help="규칙 카탈로그 JSON 만 출력")
    ap.add_argument("--facts-load", nargs="+", metavar="JSON",
                    help="데이터시트 사실 파일을 부품 DB 에 넣는다")
    ap.add_argument("--facts", action="store_true", help="부품 DB 크기를 본다")
    ap.add_argument("--extract", metavar="PDF", help="데이터시트 PDF 에서 사실을 뽑는다 (LLM)")
    ap.add_argument("--mpn", help="--extract 대상 부품번호")
    ap.add_argument("--source-url", help="--extract 한 PDF 를 받은 주소")
    ap.add_argument("--source-tier", default="unofficial",
                    choices=["official", "distributor", "unofficial"])
    ap.add_argument("--pages", metavar="N-M", help="읽을 쪽 범위 (예: 15-19)")
    ap.add_argument("--db", default=os.getenv("PREFAB_DB", "prefab.db"),
                    help="SQLite 파일 (기본: PREFAB_DB 또는 prefab.db)")
    args = ap.parse_args(argv)

    if args.extract:
        if not (args.mpn and args.source_url):
            ap.error("--extract 에는 --mpn 과 --source-url 이 필요합니다")
        return _extract(args)

    if args.facts_load:
        return _facts_load(args.facts_load, args.db)

    if args.facts:
        return _facts_list(args.db)

    if args.rules_json:
        print(json.dumps(build_rules_catalog(), ensure_ascii=False, indent=2))
        return 0

    if not args.netlist:
        ap.error("넷리스트 파일이 필요합니다.")

    path = Path(args.netlist)
    if not path.exists():
        print(f"파일을 찾지 못했습니다: {path}", file=sys.stderr)
        return 2

    sources = None
    firmware_name = None
    if args.firmware:
        fw = Path(args.firmware)
        if not fw.exists():
            print(f"펌웨어 경로를 찾지 못했습니다: {fw}", file=sys.stderr)
            return 2
        sources = load_zip(fw.read_bytes()) if fw.is_file() else load_directory(fw)
        if not sources:
            print(f"펌웨어에서 소스 파일을 찾지 못했습니다: {fw}", file=sys.stderr)
            return 2
        firmware_name = fw.name

    bom_bytes = None
    bom_name = None
    if args.bom:
        bom_path = Path(args.bom)
        if not bom_path.exists():
            print(f"BOM 을 찾지 못했습니다: {bom_path}", file=sys.stderr)
            return 2
        # 인코딩 판별은 파서가 한다 (BOM 마커·cp949). 여기서 미리 디코드하지 않는다
        bom_bytes = bom_path.read_bytes()
        bom_name = bom_path.name

    try:
        analysis = analyze(
            path.read_text(encoding="utf-8", errors="replace"),
            filename=path.name,
            bom_bytes=bom_bytes,
            firmware_sources=sources,
            fact_store=FactStore(os.getenv("PREFAB_DB", "prefab.db")),
        )
    except (NetlistParseError, BomParseError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        result = build_result(
            check_id=FIXED_CHECK_ID,
            created_at=FIXED_CREATED_AT,
            analysis=analysis,
            netlist_filename=path.name,
            bom_filename=bom_name,
            firmware_filename=firmware_name,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_human(analysis, path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
