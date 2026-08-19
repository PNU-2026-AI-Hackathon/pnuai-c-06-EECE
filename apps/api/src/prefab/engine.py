"""규칙 실행 → Finding 수집 → 정렬.

CLAUDE.md 2-4: 규칙이 NEEDS 로 선언한 입력이 없으면 '건너뜀'으로 표시한다.
조용히 통과시키지 않는다. 못 돌린 규칙이 '이상 없음'처럼 보이는 응답은 만들지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from . import catalog, rules
from .types import (
    SEVERITY_RANK,
    Context,
    Finding,
    Verdict,
    sort_findings,
)

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

    result.findings = sort_findings(dedupe(result.findings))
    return result


def dedupe(findings: list[Finding]) -> list[Finding]:
    """같은 네트에서 **새로운 근거를 하나도 못 내놓는 발견**을 합친다.

    R11 과 R12 는 같은 상황을 다른 각도로 본다 — 하나는 "이름이 거짓말한다",
    하나는 "전압이 안 맞는다". 근거는 똑같은 넷리스트 줄이다. 둘 다 띄우면
    사용자는 **같은 근거를 두 번 읽는다.** 린터가 꺼지는 이유가 그거다 (2-3).

    **네트가 같다고 무조건 합치면 안 된다.** `_IN_ACTIVE_LOW` 에는 R12(전압 도메인)와
    R08(코드가 이 핀을 안 씀)이 같이 뜨는데, 이 둘은 완전히 다른 문제이고 R08 은
    펌웨어 근거를 들고 온다. 심각도로만 고르면 **차별 등급 R08 이 기본 등급 R12 에
    먹힌다** — 우리 제품의 핵심이 사라진다. 실제로 그렇게 만들었다가 걸렸다.

    그래서 기준은 심각도가 아니라 **근거**다. 가려질 발견이 남을 발견에 없는
    근거 종류를 하나라도 들고 있으면 합치지 않는다.

    **버리지 않고 합친다.** 남긴 발견의 `suggestion` 에 가려진 규칙을 적는다.
    계약에 없는 필드를 새로 만들지 않으면서 못 한 말을 남기는 방법이다 (2-4).

    네트가 없는 발견(핀 단위, R07 같은)은 서로 다른 핀 얘기라 묶지 않는다.
    """
    by_net: dict[str, list[Finding]] = {}
    out: list[Finding] = []

    for f in findings:
        if not f.net:
            out.append(f)  # 핀 단위 발견은 네트로 묶을 수 없다
        else:
            by_net.setdefault(f.net, []).append(f)

    for group in by_net.values():
        out.extend(_merge_group(group))

    return out


def _merge_group(group: list[Finding]) -> list[Finding]:
    """한 네트의 발견들을 필요한 만큼만 합친다."""
    if len(group) == 1:
        return group

    remaining = sorted(group, key=_rank)
    kept: list[Finding] = []
    absorbed: dict[int, list[Finding]] = {}

    for finding in remaining:
        host = next(
            (i for i, k in enumerate(kept) if _adds_nothing(finding, k)),
            None,
        )
        if host is None:
            kept.append(finding)
        else:
            absorbed.setdefault(host, []).append(finding)

    return [_absorb(f, absorbed.get(i, [])) for i, f in enumerate(kept)]


def _adds_nothing(candidate: Finding, keeper: Finding) -> bool:
    """`candidate` 가 `keeper` 에 없는 근거 종류를 하나도 못 내놓는가."""
    return {e.kind for e in candidate.evidence} <= {e.kind for e in keeper.evidence}


def _rank(f: Finding) -> tuple[int, int, str]:
    """어느 발견을 남길지. **미결·어긋남이 해제보다 앞선다** — 열린 문제가 먼저다."""
    return (0 if f.verdict is not Verdict.PASS else 1, SEVERITY_RANK[f.severity], f.rule)


def _absorb(kept: Finding, hidden: list[Finding]) -> Finding:
    """가려진 발견을 남긴 발견의 처방에 적어 넣는다."""
    if not hidden:
        return kept
    names = " · ".join(f"{h.rule}({h.title})" for h in sorted(hidden, key=_rank))
    note = f"이 네트에는 {names} 도 함께 해당합니다."
    return replace(kept, suggestion=f"{kept.suggestion} {note}".strip())
