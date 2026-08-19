"""검증 측정 (E-3) — 라벨된 케이스에 엔진을 돌려 숫자를 낸다.

**"정확도 얼마예요"에 답하기 위한 파일이다.** 지금까지는 답이 없었다.

두 숫자를 낸다.

```
검출   기대한 규칙이 실제로 떴는가        놓치면 미검출
오탐   기대 안 한 규칙이 떴는가          뜨면 오탐
```

`expect` 는 **정확히 그 규칙들만** 떠야 한다는 뜻이다. 느슨하게 세면 숫자가
거짓말을 한다 — 오탐을 세는 것이 이 파일의 목적인데 오탐을 봐주면 의미가 없다.

**LLM 을 판정자로 쓰지 않는다.** 정답은 우리가 만든 라벨이다 (`결정_기록.md` D-1).
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .datasheet.store import FactStore
from .runner import analyze


@dataclass
class CaseResult:
    """케이스 하나의 결과."""

    id: str
    kind: str
    expected: list[str]
    fired: list[str]

    @property
    def missed(self) -> list[str]:
        """기대했는데 안 뜬 규칙 — 미검출."""
        return [r for r in self.expected if r not in self.fired]

    @property
    def spurious(self) -> list[str]:
        """기대 안 했는데 뜬 규칙 — 오탐."""
        return [r for r in self.fired if r not in self.expected]

    @property
    def ok(self) -> bool:
        return not self.missed and not self.spurious


@dataclass
class Report:
    cases: list[CaseResult] = field(default_factory=list)
    #: 읽지 못한 케이스. 조용히 빼면 숫자가 좋아 보인다 (CLAUDE.md 2-4).
    errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def expected_total(self) -> int:
        return sum(len(c.expected) for c in self.cases)

    @property
    def detected(self) -> int:
        return sum(len(c.expected) - len(c.missed) for c in self.cases)

    @property
    def spurious_total(self) -> int:
        return sum(len(c.spurious) for c in self.cases)

    @property
    def recall(self) -> float | None:
        """검출율. 기대한 것이 하나도 없으면 잴 수 없다 — 0 이 아니라 None 이다."""
        return self.detected / self.expected_total if self.expected_total else None

    @property
    def clean_cases(self) -> list[CaseResult]:
        """결함이 없다고 라벨한 케이스. 오탐율은 여기서 나온다."""
        return [c for c in self.cases if not c.expected]

    @property
    def false_positive_rate(self) -> float | None:
        """결함 없는 케이스 중 경고가 뜬 비율."""
        clean = self.clean_cases
        if not clean:
            return None
        return sum(1 for c in clean if c.spurious) / len(clean)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cases": len(self.cases),
            "expected": self.expected_total,
            "detected": self.detected,
            "recall": self.recall,
            "clean_cases": len(self.clean_cases),
            "spurious": self.spurious_total,
            "false_positive_rate": self.false_positive_rate,
            "errors": len(self.errors),
        }


def run(folder: str | Path, *, db_path: str | Path | None = None) -> Report:
    """`MANIFEST.json` 이 있는 폴더를 통째로 돌린다."""
    folder = Path(folder)
    manifest = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))

    report = Report()
    for case in manifest.get("cases", []):
        try:
            report.cases.append(_run_case(folder, case, db_path))
        except Exception as exc:  # 한 케이스가 죽어도 나머지는 잰다
            report.errors.append((case.get("id", "?"), f"{type(exc).__name__}: {exc}"))
    return report


def _run_case(folder: Path, case: dict[str, Any], db_path: str | Path | None) -> CaseResult:
    netlist = (folder / case["netlist"]).read_text(encoding="utf-8")

    bom_bytes = None
    if case.get("bom"):
        bom_bytes = (folder / case["bom"]).read_bytes()

    sources: dict[str, str] | None = None
    if case.get("firmware"):
        folder_fw = folder / case["firmware"]
        sources = {
            f.name: f.read_text(encoding="utf-8")
            for f in sorted(folder_fw.iterdir())
            if f.is_file()
        }

    store = None
    if case.get("facts"):
        # 케이스마다 새 DB 를 쓴다. 앞 케이스의 사실이 새어 들어가면 숫자가 거짓말한다.
        # `:memory:` 는 못 쓴다 — 연결을 매번 새로 여는 구조라 표가 사라진다.
        store = FactStore(db_path or Path(tempfile.mkdtemp()) / "case.db")
        for payload in json.loads((folder / case["facts"]).read_text(encoding="utf-8")):
            store.save(payload)

    analysis = analyze(
        netlist,
        filename=case["netlist"],
        bom_bytes=bom_bytes,
        firmware_sources=sources,
        fact_store=store,
    )
    # 해제(PASS)는 경고가 아니다. 뜬 것으로 세지 않는다.
    fired = sorted({f.rule for f in analysis.engine.findings if f.verdict.value != "PASS"})
    return CaseResult(
        id=case["id"],
        kind=case.get("kind", ""),
        expected=list(case.get("expect", [])),
        fired=fired,
    )


def format_report(report: Report) -> str:
    """사람이 읽는 표. 발표에 그대로 쓸 수 있어야 한다."""
    out: list[str] = []
    bar = "=" * 66
    out.append(bar)
    out.append("검증 측정 — 결함 주입 데이터셋")
    out.append(bar)

    for c in report.cases:
        mark = "OK " if c.ok else "!! "
        out.append(f"{mark}{c.id:24} {c.kind:3} 기대={c.expected or '없음'} 실제={c.fired or '없음'}")
        if c.missed:
            out.append(f"     미검출: {', '.join(c.missed)}")
        if c.spurious:
            out.append(f"     오탐:   {', '.join(c.spurious)}")

    for case_id, why in report.errors:
        out.append(f"?? {case_id:24} 읽지 못함 — {why}")

    out.append(bar)
    recall = report.recall
    fpr = report.false_positive_rate
    out.append(
        f"검출  {report.detected}/{report.expected_total}"
        + (f" ({recall:.0%})" if recall is not None else " (잴 수 없음)")
    )
    out.append(
        f"오탐  결함 없는 케이스 {len(report.clean_cases)}개 중 "
        f"{sum(1 for c in report.clean_cases if c.spurious)}개에서 발생"
        + (f" ({fpr:.0%})" if fpr is not None else "")
    )
    if report.errors:
        out.append(f"읽지 못한 케이스 {len(report.errors)}개 — 숫자에서 빠져 있습니다")
    out.append(bar)

    # 숫자만 떼어 인용되면 안 된다. 이 데이터셋이 무엇을 재고 무엇을 못 재는지 붙인다.
    synthetic = sum(1 for c in report.cases if c.kind != "실측")
    out.append(
        f"이 숫자가 재는 것: 케이스 {len(report.cases)}개 (합성 {synthetic} · 실측 "
        f"{len(report.cases) - synthetic}). 합성 케이스는 우리가 만들었으므로 "
        "정답을 안다."
    )
    out.append(
        "이 숫자가 못 재는 것: **남의 보드에서의 재현율.** 오픈소스 커밋 라벨링"
        "(E-1)이 아직 없다. 외부 검증이 아니라 회귀 방지에 가깝다."
    )
    out.append(bar)
    return "\n".join(out)
