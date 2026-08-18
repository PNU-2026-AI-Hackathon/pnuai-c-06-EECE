"""데이터시트 PDF → 전기적 사실 (LLM 추출).

**LLM 은 읽기만 한다. 판정은 코드가 한다** (CLAUDE.md 2-1). 여기서 LLM 이 하는 일은
"몇 쪽 어느 표에 이렇게 써 있다"고 제안하는 것까지다. 그 제안이 진짜인지는
**결정적 코드가 원문과 대조해서 확인한다.**

```
LLM     17쪽 Table 2 에 "A GPIO, IO level 3.3V" 라고 써 있고 Voh 는 3.3V 다
코드    17쪽 원문에 그 문장이 실제로 있는가?  없으면 버린다
저장기  출처(page·quote)가 없으면 애초에 안 받는다 (store.py)
규칙    3.3 <= 3.6 비교는 순수 함수가 한다 (rules/_clearance.py)
```

지어낸 인용문은 두 번째 단계에서 걸린다. 그게 이 파일의 존재 이유다.
`결정_기록.md` D-1 "AI 가 제안하고 결정적 코드가 검증한다" 를 추출에 적용한 것이다.

네트워크를 부르는 유일한 자리이므로 **규칙은 이 파일을 import 하지 않는다.**
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol

from .facts import (
    CONF_HIGH,
    CONF_LOW,
    CONF_MEDIUM,
    CONF_NONE,
    FIELD_LABELS,
    TIER_DISTRIBUTOR,
    TIER_OFFICIAL,
    TIER_UNOFFICIAL,
)

#: 추출에 쓸 모델. 스키마를 강제할 수 있는 모델이어야 한다.
MODEL = "claude-opus-5"

#: 추출 응답은 짧다. 스트리밍이 필요한 크기가 아니다.
MAX_TOKENS = 16000

#: 인용문 대조 시 무시할 차이 — **공백 전부**.
#:
#: 처음엔 공백을 하나로 줄이기만 했는데, 실측 PDF 에서 진짜 인용문이 지어낸 것으로
#: 판정됐다. 데이터시트의 글자 레이어는 공백을 통째로 잃어버린다 —
#: 화면에는 `A GPIO, IO level 3.3V` 인데 뽑으면 `AGPIO,IO level 3.3V` 다.
#: 공백은 이 검증에서 아무 뜻도 없고, 지어낸 인용은 공백이 아니라 **글자**가 다르다.
#: `3.3V` 와 `3.5V` 는 여전히 걸린다.
_SPACE = re.compile(r"\s+")


class Client(Protocol):
    """`anthropic.Anthropic` 중 우리가 쓰는 부분만.

    이렇게 좁혀 두면 **키 없이도 테스트가 전부 돈다.** 가짜 클라이언트를 넣으면 된다.
    """

    @property
    def messages(self) -> Any: ...


@dataclass(frozen=True)
class Page:
    """PDF 한 쪽. `number` 는 사람이 세는 번호(1부터)다."""

    number: int
    text: str


@dataclass
class Dropped:
    """검증에서 떨어진 제안. **조용히 버리지 않는다** (CLAUDE.md 2-4)."""

    field: str
    why: str


@dataclass
class Extraction:
    """추출 결과.

    `payload` 는 `store.save()` 에 그대로 넘길 수 있는 모양이다.
    떨어뜨린 것은 `dropped` 에 이유와 함께 남는다.
    """

    payload: dict[str, Any]
    dropped: list[Dropped] = field(default_factory=list)
    #: 모델이 실제로 돌려준 원본. 검증 전 상태를 되짚을 수 있어야 한다.
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def facts(self) -> list[dict[str, Any]]:
        return self.payload.get("facts", [])

    @property
    def ok(self) -> bool:
        return not self.dropped


class ExtractionError(RuntimeError):
    """추출을 끝내지 못했다. 사실이 없는 것과 다르다."""


# ── 스키마 — 자유 텍스트로 받지 않는다 (prefab-datasheet 5단계) ──────────

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "enum": sorted(FIELD_LABELS)},
                    # 숫자 항목과 문자 항목이 섞여 있어 둘 다 받는다.
                    "value_number": {"type": ["number", "null"]},
                    "value_text": {"type": ["string", "null"]},
                    "unit": {"type": ["string", "null"]},
                    "table": {"type": ["string", "null"]},
                    "page": {"type": ["integer", "null"]},
                    "quote": {"type": ["string", "null"]},
                    "confidence": {
                        "type": "string",
                        "enum": [CONF_HIGH, CONF_MEDIUM, CONF_LOW, CONF_NONE],
                    },
                    "reason": {"type": ["string", "null"]},
                },
                "required": [
                    "field", "value_number", "value_text", "unit",
                    "table", "page", "quote", "confidence", "reason",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["facts"],
    "additionalProperties": False,
}

SYSTEM = """\
당신은 전자부품 데이터시트에서 전기적 정격을 읽어내는 사람입니다.

**절대 원칙: 모르면 값을 비웁니다. 추정값을 넣지 않습니다.**
틀린 값 하나는 그 부품을 쓰는 모든 사용자에게 오탐 또는 미검출을 만듭니다.
"아마 3.3V일 것"은 넣으면 안 되는 값입니다.

규칙입니다.

- `quote` 는 **PDF 원문 그대로** 옮깁니다. 번역·요약·재구성 하지 않습니다.
  옮긴 문장이 그 쪽 원문에 글자 그대로 없으면 그 항목은 버려집니다.
- `page` 는 그 문장이 실제로 있는 쪽 번호입니다. 짐작해서 적지 않습니다.
- 값이 없으면 `value_number` 와 `value_text` 를 둘 다 null 로 두고,
  `confidence` 를 "none" 으로, `reason` 에 왜 없는지 적습니다. 이건 실패가 아니라
  정상적인 결과입니다.
- **Absolute Maximum 과 Recommended Operating 을 섞지 않습니다.** 전자는
  "넘으면 파손", 후자는 "이 범위에서 정상 동작"입니다. 판정 기준이 다르므로
  `table` 에 어느 표에서 읽었는지 반드시 적습니다.
- 정격 표(min/max 열이 있는 표)를 본문 서술보다 우선합니다. 본문에서 유추했으면
  `confidence` 를 "low" 로 둡니다.
"""

_FIELD_GUIDE = "\n".join(f"- `{k}` — {v}" for k, v in sorted(FIELD_LABELS.items()))


def build_prompt(mpn: str, pages: Iterable[Page]) -> str:
    """쪽 번호를 붙여서 넘긴다. 번호가 없으면 출처를 검증할 수 없다."""
    body = "\n\n".join(f"=== {p.number}쪽 ===\n{p.text}" for p in pages)
    return (
        f"부품번호: {mpn}\n\n"
        f"찾을 항목입니다. 문서에 없는 항목은 값을 비우고 이유를 적으세요.\n{_FIELD_GUIDE}\n\n"
        f"--- 데이터시트 본문 ---\n{body}\n"
    )


# ── 추출 ────────────────────────────────────────────────────────────


def extract(
    client: Client,
    *,
    mpn: str,
    pages: list[Page],
    source_url: str,
    source_tier: str = TIER_UNOFFICIAL,
    model: str = MODEL,
) -> Extraction:
    """데이터시트 본문에서 사실을 뽑는다.

    돌려주는 `payload` 는 `FactStore.save()` 가 그대로 받는 모양이다.
    **인용문이 원문에 없는 항목은 여기서 이미 빠져 있다.**
    """
    if source_tier not in (TIER_OFFICIAL, TIER_DISTRIBUTOR, TIER_UNOFFICIAL):
        raise ValueError(f"모르는 출처 등급: {source_tier}")
    if not pages:
        raise ValueError("본문이 비어 있습니다")

    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": build_prompt(mpn, pages)}],
    )

    raw = _read_json(response)
    return _verify(
        raw, mpn=mpn, pages=pages, source_url=source_url, source_tier=source_tier
    )


def _read_json(response: Any) -> dict[str, Any]:
    """스키마를 강제했으므로 첫 text 블록이 곧 JSON 이다."""
    if getattr(response, "stop_reason", None) == "refusal":
        raise ExtractionError("모델이 응답을 거절했습니다")

    for block in response.content:
        if getattr(block, "type", None) == "text":
            try:
                return json.loads(block.text)
            except json.JSONDecodeError as exc:
                raise ExtractionError(f"응답이 JSON 이 아닙니다 — {exc}") from exc
    raise ExtractionError("응답에 본문이 없습니다")


# ── 검증 — 여기가 이 파일의 핵심이다 ─────────────────────────────────


def _verify(
    raw: dict[str, Any],
    *,
    mpn: str,
    pages: list[Page],
    source_url: str,
    source_tier: str,
) -> Extraction:
    """모델이 말한 인용문이 그 쪽 원문에 정말 있는지 대조한다.

    없으면 버린다. **지어낸 출처가 DB 에 들어가는 것이 이 파이프라인의
    가장 큰 위험이고, 막을 수 있는 자리는 여기뿐이다.**
    """
    by_page = {p.number: _flat(p.text) for p in pages}
    facts: list[dict[str, Any]] = []
    dropped: list[Dropped] = []

    for item in raw.get("facts", []):
        name = item.get("field", "?")
        value = item.get("value_number")
        if value is None:
            value = item.get("value_text")

        if value is None:
            # 값이 없다는 것도 사실이다. 다만 이유는 있어야 한다.
            if not item.get("reason"):
                dropped.append(Dropped(name, "값이 없는데 왜 없는지를 안 적었습니다"))
                continue
            facts.append(_fact(item, value=None))
            continue

        page, quote = item.get("page"), item.get("quote")
        if not page or not quote:
            dropped.append(Dropped(name, "값은 말했는데 몇 쪽 어느 문장인지를 안 적었습니다"))
            continue
        if page not in by_page:
            dropped.append(Dropped(name, f"{page}쪽은 넘겨준 본문에 없습니다"))
            continue
        if _flat(quote) not in by_page[page]:
            dropped.append(
                Dropped(name, f"{page}쪽 원문에 그 문장이 없습니다 — 인용이 지어졌습니다")
            )
            continue

        facts.append(_fact(item, value=value))

    return Extraction(
        payload={
            "mpn": mpn,
            "source_url": source_url,
            "source_tier": source_tier,
            "facts": facts,
        },
        dropped=dropped,
        raw=raw,
    )


def _fact(item: dict[str, Any], *, value: Any) -> dict[str, Any]:
    """`store.save()` 가 받는 모양으로 옮긴다."""
    return {
        "field": item["field"],
        "value": value,
        "unit": item.get("unit"),
        "table": item.get("table"),
        "page": item.get("page"),
        "quote": item.get("quote"),
        "confidence": item.get("confidence") or CONF_NONE,
        "reason": item.get("reason"),
    }


def _flat(text: str) -> str:
    """공백을 전부 지우고 비교한다. 이유는 `_SPACE` 주석에 있다.

    공백 말고는 봐주지 않는다.
    """
    return _SPACE.sub("", text)
