"""규칙 실행 → Finding 수집 → 정렬.

CLAUDE.md 2-4: 규칙이 NEEDS 로 선언한 입력이 없으면 '건너뜀'으로 표시한다.
조용히 통과시키지 않는다. 못 돌린 규칙이 '이상 없음'처럼 보이는 응답은 만들지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import catalog, rules
from .types import Context, Finding, sort_findings

#: 건너뛴 이유
SKIP_NOT_IMPLEMENTED = "not_implemented"
SKIP_MISSING_INPUT = "missing_input"


@dataclass(frozen=True)
class Skipped:
    rule: str
    reason: str
    detail: str


@dataclass
class EngineResult:
    findings: list[Finding] = field(default_factory=list)
    ran: list[str] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)

    @property
    def total(self) -> int:
        return catalog.TOTAL

    @property
    def skipped_not_implemented(self) -> list[Skipped]:
        return [s for s in self.skipped if s.reason == SKIP_NOT_IMPLEMENTED]

    @property
    def skipped_missing_input(self) -> list[Skipped]:
        return [s for s in self.skipped if s.reason == SKIP_MISSING_INPUT]


def run(ctx: Context) -> EngineResult:
    """카탈로그 전체를 훑는다. 실행한 것과 건너뛴 것이 언제나 합쳐서 카탈로그 전체다."""
    result = EngineResult()

    for spec in catalog.CATALOG:
        module = rules.BY_ID.get(spec.id)

        if module is None:
            result.skipped.append(
                Skipped(spec.id, SKIP_NOT_IMPLEMENTED, spec.blocked_by or "미구현")
            )
            continue

        missing = ctx.missing(module.NEEDS)
        if missing:
            result.skipped.append(
                Skipped(spec.id, SKIP_MISSING_INPUT, f"{' · '.join(missing)} 없음")
            )
            continue

        result.findings.extend(module.check(ctx))
        result.ran.append(spec.id)

    result.findings = sort_findings(result.findings)
    return result
