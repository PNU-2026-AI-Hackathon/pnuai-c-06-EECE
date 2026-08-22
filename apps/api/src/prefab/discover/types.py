"""후보 하나의 모양. **`Finding` 과 일부러 다르게 생겼다.**

`Finding` 은 판정이라 `verdict` 와 `severity` 를 가진다. `Candidate` 는 제안이라
그 둘이 없다 — **후보에 심각도를 붙이면 화면에서 발견처럼 보인다.**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Citation:
    """후보가 지목한 자리. **코드가 실재를 확인할 수 있어야 한다.**

    `kind` 로 어디를 가리키는지 가른다 — 검증기가 그 종류에 맞는 방법으로 확인한다.
    """

    #: `firmware` 면 파일의 줄, `netlist` 면 부품·핀
    kind: str
    #: 펌웨어: 파일 경로 / 넷리스트: 부품기호
    where: str
    #: 펌웨어: 줄 번호 / 넷리스트: 핀 이름
    what: str | None = None
    #: 그 자리에 있다고 주장하는 원문
    quote: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "where": self.where, "what": self.what, "quote": self.quote}


@dataclass(frozen=True)
class Candidate:
    """규칙 후보 하나.

    **판정이 아니다.** 그래서 `verdict` 도 `severity` 도 없다.
    """

    #: 한 줄 제목. 규칙이 된다면 그 규칙의 제목이 될 말
    title: str
    #: 무엇이 위험한지 사람 말로
    why: str
    #: 이 후보가 지목한 자리들. 비면 검증에서 탈락한다
    citations: tuple[Citation, ...] = ()
    #: 이 모양을 이미 보는 기존 규칙이 있으면 그 id. 있으면 후보가 아니다
    covered_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "why": self.why,
            "citations": [c.to_dict() for c in self.citations],
            "covered_by": self.covered_by,
        }


@dataclass(frozen=True)
class Proposal:
    """한 번의 발견 시도 결과.

    **버린 것을 같이 들고 다닌다.** 몇 개를 왜 버렸는지 말하지 않으면
    "LLM 이 두 개 찾았습니다" 가 "LLM 이 두 개만 말했습니다" 로 읽힌다 (헌법 2-4).
    """

    kept: tuple[Candidate, ...] = ()
    #: (후보 제목, 버린 이유)
    dropped: tuple[tuple[str, str], ...] = ()
    #: 모델을 못 불렀으면 그 사유. 부르지 않은 것과 못 부른 것은 다르다
    unavailable: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates": [c.to_dict() for c in self.kept],
            "dropped": [{"title": t, "reason": r} for t, r in self.dropped],
            "unavailable": self.unavailable,
            "notes": list(self.notes),
        }
