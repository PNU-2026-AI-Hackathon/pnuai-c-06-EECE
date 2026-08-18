"""규칙이 의존하는 유일한 타입 묶음.

CLAUDE.md 2-1: 판정 함수는 순수 함수다. 이 모듈은 표준 라이브러리만 쓴다.
API_CONTRACT.md 의 finding 객체와 1:1로 대응한다. 계약에 없는 필드를 만들지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class Verdict(str, Enum):
    FAIL = "FAIL"
    PASS = "PASS"
    UNRESOLVED = "UNRESOLVED"


Tier = Literal["기본", "차별"]
EvidenceKind = Literal["netlist", "firmware", "datasheet"]

#: 리포트 정렬 순서. 낮을수록 위에 온다.
SEVERITY_RANK: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
}

#: 규칙이 NEEDS 로 선언할 수 있는 입력 이름. 계약의 RuleInfo.needs 와 같은 어휘다.
#: 엔진이 아는 입력 이름. `Context` 필드명과 1:1 이다.
#:
#: **계약(`docs/API_CONTRACT.md`)의 `RuleInfo.needs` 는 아직 앞의 세 개만 노출한다.**
#: `datasheet` 는 엔진이 사실 DB 조회 결과를 실어 나르기 위해 먼저 뚫어 둔 자리라서,
#: 카탈로그의 `needs` 에 쓰면 프론트가 모르는 값이 나간다. 계약을 먼저 고치고 쓴다.
INPUT_NAMES = ("netlist", "bom", "firmware", "datasheet")

#: 계약이 프론트에 약속한 `needs` 어휘. 카탈로그는 이 밖으로 나가면 안 된다.
CONTRACT_NEEDS = ("netlist", "bom", "firmware")


@dataclass(frozen=True)
class Evidence:
    """근거 하나. kind 에 따라 채워지는 필드가 다르다.

    직접 생성하지 말고 Evidence.netlist / .firmware / .datasheet 를 쓴다.
    """

    kind: EvidenceKind
    # kind == "netlist"
    text: str | None = None
    # kind == "firmware"
    file: str | None = None
    line: int | None = None
    snippet: str | None = None
    # kind == "datasheet"
    mpn: str | None = None
    table: str | None = None
    page: int | None = None
    quote: str | None = None
    # 공통 — 프론트에서 강조 표시할 토큰
    highlight: tuple[str, ...] = ()

    @classmethod
    def netlist(cls, text: str, highlight: tuple[str, ...] | list[str] = ()) -> "Evidence":
        return cls(kind="netlist", text=text, highlight=tuple(highlight))

    @classmethod
    def firmware(
        cls,
        file: str,
        line: int,
        snippet: str,
        highlight: tuple[str, ...] | list[str] = (),
    ) -> "Evidence":
        return cls(kind="firmware", file=file, line=line, snippet=snippet, highlight=tuple(highlight))

    @classmethod
    def datasheet(
        cls,
        mpn: str,
        table: str,
        page: int,
        quote: str,
        highlight: tuple[str, ...] | list[str] = (),
    ) -> "Evidence":
        return cls(kind="datasheet", mpn=mpn, table=table, page=page, quote=quote, highlight=tuple(highlight))

    def to_dict(self) -> dict[str, Any]:
        """계약의 discriminated union 그대로. 해당 kind 에 없는 키는 아예 넣지 않는다."""
        if self.kind == "netlist":
            out: dict[str, Any] = {"kind": "netlist", "text": self.text}
        elif self.kind == "firmware":
            out = {"kind": "firmware", "file": self.file, "line": self.line, "snippet": self.snippet}
        elif self.kind == "datasheet":
            out = {
                "kind": "datasheet",
                "mpn": self.mpn,
                "table": self.table,
                "page": self.page,
                "quote": self.quote,
            }
        else:  # pragma: no cover - 방어
            raise ValueError(f"알 수 없는 근거 종류: {self.kind}")
        if self.highlight:
            out["highlight"] = list(self.highlight)
        return out


@dataclass(frozen=True)
class Finding:
    """규칙 하나가 내놓은 발견 하나."""

    rule: str
    title: str
    tier: Tier
    severity: Severity
    verdict: Verdict
    net: str | None
    claim: str
    evidence: tuple[Evidence, ...] = ()
    suggestion: str | None = None
    #: 판정을 못 내린 이유. 판정했으면 None. 지어내지 않는다.
    unresolved_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "title": self.title,
            "tier": self.tier,
            "severity": self.severity.value,
            "verdict": self.verdict.value,
            "net": self.net,
            "claim": self.claim,
            "evidence": [e.to_dict() for e in self.evidence],
            "suggestion": self.suggestion,
            "unresolved_reason": self.unresolved_reason,
        }


@dataclass(frozen=True)
class Context:
    """규칙 하나가 볼 수 있는 세상 전부.

    firmware / datasheet / git / chip 은 아직 None 일 수 있다.
    규칙이 NEEDS 로 선언한 입력이 없으면 엔진이 그 규칙을 '건너뜀'으로 표시한다.
    조용히 통과시키지 않는다.
    """

    netlist: Any = None
    bom: Any = None
    firmware: Any = None
    datasheet: Any = None
    git: Any = None
    chip: Any = None

    def available(self) -> set[str]:
        """지금 손에 있는 입력 이름들. NEEDS 와 같은 어휘를 쓴다."""
        return {name for name in INPUT_NAMES if getattr(self, name) is not None}

    def missing(self, needs: "list[str] | tuple[str, ...]") -> list[str]:
        have = self.available()
        return [n for n in needs if n not in have]


def sort_findings(findings: "list[Finding] | tuple[Finding, ...]") -> list[Finding]:
    """심각도 → 규칙 ID → 네트명. 같은 입력이면 항상 같은 순서가 나온다."""
    return sorted(findings, key=lambda f: (SEVERITY_RANK[f.severity], f.rule, f.net or ""))
