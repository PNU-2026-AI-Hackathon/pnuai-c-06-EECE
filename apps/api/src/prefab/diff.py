"""검사 결과 커밋 간 비교 (F-1).

**드리프트를 R10 없이 보여주는 자리다** (`결정_기록.md` D-2).

R10(회로도 변경 후 코드 미추종)은 git 이력을 계약의 네 번째 입력으로 받아야 해서
아직 없다. 그런데 드리프트를 **보여주는** 데는 그게 필요 없다 — 같은 엔진을
두 커밋의 입력에 돌려서 발견 목록이 어떻게 달라졌는지 비교하면 된다.
회로도를 고쳤는데 코드를 안 고쳤으면, 그 PR 에서 발견이 새로 생긴다.

## 두 커밋을 어떻게 비교하나

**엔진은 한 벌만 쓴다.** 지금(HEAD) 코드로 예전 입력과 지금 입력을 각각 돌린다.

```
prefab(HEAD 코드, base 입력)  →  before.json
prefab(HEAD 코드, head 입력)  →  after.json
```

예전 코드로 예전 입력을 돌리면 **규칙을 고친 것과 보드를 고친 것이 섞인다.**
R09 를 추가한 PR 이 "보드가 나빠졌다"로 보이면 이 도구는 못 쓴다.

## 무엇으로 같은 발견이라고 보나

`(규칙 · 네트 · 지목한 자리)` 세 개다. `claim` 문구는 쓰지 않는다 — 근거 문구를
다듬기만 해도 전부 "새 발견"으로 보이면 아무도 안 읽는다 (헌법 11절을 지키는 대가).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: 새로 생기면 CI 를 빨간불로 만드는 심각도
BLOCKING_SEVERITY = "CRITICAL"

#: 판정이 안 난 것은 실패로 세지 않는다. 모른다는 것은 나빠진 것이 아니다.
FAILED = "FAIL"


def finding_key(f: dict[str, Any]) -> tuple[str, str, str]:
    """같은 발견인지 가르는 신원.

    `claim` 은 일부러 뺐다. 문구를 다듬은 PR 이 전부 '새 발견'으로 뜨면
    이 도구는 첫 주에 꺼진다 (헌법 2-3 — 오탐이 최우선 적이다).
    """
    sites = sorted({
        h
        for ev in (f.get("evidence") or [])
        for h in (ev.get("highlight") or [])
        if "." in h  # `U1.D2` 처럼 부품.핀 을 지목한 것만 자리로 친다
    })
    return (f.get("rule", ""), f.get("net") or "", " · ".join(sites))


def _label(f: dict[str, Any]) -> str:
    key = finding_key(f)
    where = key[1] or key[2] or "—"
    return f"{key[0]} · {where}"


@dataclass(frozen=True)
class VerdictChange:
    """같은 발견인데 판정이 달라진 것. 해제(FAIL→PASS)가 여기 잡힌다."""

    before: dict[str, Any]
    after: dict[str, Any]

    @property
    def label(self) -> str:
        return _label(self.after)

    @property
    def arrow(self) -> str:
        return f"{self.before.get('verdict')} → {self.after.get('verdict')}"

    @property
    def cleared(self) -> bool:
        return self.before.get("verdict") == FAILED and self.after.get("verdict") == "PASS"


@dataclass
class Diff:
    added: list[dict[str, Any]] = field(default_factory=list)
    removed: list[dict[str, Any]] = field(default_factory=list)
    changed: list[VerdictChange] = field(default_factory=list)
    before_summary: dict[str, Any] = field(default_factory=dict)
    after_summary: dict[str, Any] = field(default_factory=dict)
    #: 규칙이 늘거나 줄었으면 적는다. 비교가 사과 대 오렌지가 되는 유일한 경우다.
    notes: list[str] = field(default_factory=list)

    @property
    def blocking(self) -> list[dict[str, Any]]:
        """새로 생긴 치명 발견. 이게 있으면 CI 를 빨간불로 만든다."""
        return [
            f for f in self.added
            if f.get("severity") == BLOCKING_SEVERITY and f.get("verdict") == FAILED
        ]

    @property
    def quiet(self) -> bool:
        return not (self.added or self.removed or self.changed)


def diff_results(before: dict[str, Any], after: dict[str, Any]) -> Diff:
    """계약 응답 두 개를 비교한다. 순수 함수다."""
    b = {finding_key(f): f for f in before.get("findings", [])}
    a = {finding_key(f): f for f in after.get("findings", [])}

    out = Diff(
        added=[a[k] for k in a if k not in b],
        removed=[b[k] for k in b if k not in a],
        changed=[
            VerdictChange(b[k], a[k])
            for k in a
            if k in b and b[k].get("verdict") != a[k].get("verdict")
        ],
        before_summary=before.get("summary", {}),
        after_summary=after.get("summary", {}),
    )

    # 규칙 자체가 늘었으면 "보드가 나빠졌다"가 아니다. 그 사실을 숨기지 않는다.
    b_run = out.before_summary.get("rules_run")
    a_run = out.after_summary.get("rules_run")
    if b_run is not None and a_run is not None and b_run != a_run:
        out.notes.append(
            f"돌아간 규칙 수가 {b_run} → {a_run} 로 달라졌습니다. "
            "새 발견 중 일부는 보드가 아니라 **규칙이 늘어서** 나온 것일 수 있습니다."
        )
    return out


def format_diff(d: Diff, *, before_label: str = "base", after_label: str = "head") -> str:
    """PR 코멘트용 마크다운. 사람이 읽는다 — 숫자만 던지지 않는다."""
    lines: list[str] = ["## Prefab — 검사 결과 변화", ""]

    if d.quiet:
        lines += [f"`{before_label}` 와 `{after_label}` 의 발견이 같습니다. 드리프트 없음.", ""]
    else:
        lines += [f"`{before_label}` → `{after_label}`", ""]

    def block(title: str, items: list[str]) -> None:
        if not items:
            return
        lines.append(f"### {title}")
        lines.extend(items)
        lines.append("")

    block(
        f"🔴 새로 생긴 발견 {len(d.added)}건",
        [f"- **{_label(f)}** ({f.get('severity')}) — {f.get('claim', '')}" for f in d.added],
    )
    block(
        f"✅ 사라진 발견 {len(d.removed)}건",
        [f"- **{_label(f)}** ({f.get('severity')}) — {f.get('claim', '')}" for f in d.removed],
    )
    block(
        f"🔄 판정이 달라진 발견 {len(d.changed)}건",
        [
            f"- **{c.label}** {c.arrow}"
            + ("  ← 데이터시트로 해제됨" if c.cleared else "")
            for c in d.changed
        ],
    )

    b, a = d.before_summary, d.after_summary
    if b or a:
        lines += [
            "### 요약",
            "",
            "| | 치명 | 경고 | 해제 | 돌아간 규칙 |",
            "|---|---:|---:|---:|---:|",
            f"| `{before_label}` | {b.get('critical', '?')} | {b.get('warning', '?')} "
            f"| {b.get('cleared', '?')} | {b.get('rules_run', '?')} |",
            f"| `{after_label}` | {a.get('critical', '?')} | {a.get('warning', '?')} "
            f"| {a.get('cleared', '?')} | {a.get('rules_run', '?')} |",
            "",
        ]

    for note in d.notes:
        lines += [f"> ⚠ {note}", ""]

    lines += [
        "---",
        "",
        "**이 비교가 못 보는 것:** 같은 엔진(HEAD 코드)을 두 입력에 돌린 결과입니다. "
        "이 PR 이전부터 있던 문제는 양쪽에 똑같이 떠서 여기 안 나옵니다 — "
        "전체 목록은 `python -m prefab <넷리스트>` 로 보세요.",
    ]
    return "\n".join(lines)


def load(path: "str | Path") -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
