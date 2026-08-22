"""LLM 에 후보를 물어본다. **이 파일이 이 모듈에서 네트워크를 쓰는 유일한 자리다.**

`datasheet/extract.py` 와 같은 모양이다 — 모델은 읽고, 스키마로 강제하고,
**코드가 검증한다** (`verify.py`). 여기서는 검증을 하지 않는다. 부르기만 한다.

## 모델에게 무엇을 주나

    넷리스트 · 펌웨어 · **지금 가진 규칙 목록** · 이미 나온 발견

규칙 목록을 안 주면 이미 잡은 것을 또 말한다. 발견을 안 주면 같은 자리를 또 짚는다.
둘 다 주고 **"이것들이 못 보는 것"** 만 물어야 새 후보가 나온다.

## 왜 판정을 안 시키나

시켜 봤고 졌다. 남의 실제 보드 6개에서 LLM 오탐 0건 · 우리 45건이었지만,
합성 케이스에서는 LLM 이 **없는 제약을 지어냈다** (외부 플래시가 달린 정상 보드를
"플래시 전용 핀 배선" 이라고 했다). 판정을 맡기면 그런 게 검사 결과에 들어간다.
**발견자로 쓰면 그런 것은 검증에서 걸러지고, 진짜만 남는다.**
"""

from __future__ import annotations

import json
import os
from typing import Any

from .types import Candidate, Citation

#: 후보 찾기에 쓸 모델. 스키마를 강제할 수 있어야 한다.
MODEL = os.getenv("PREFAB_DISCOVER_MODEL", "claude-opus-5")

#: 출력 상한. **4000 으로 뒀다가 데였다** — 모델이 그걸 전부 생각에 쓰고
#: 답을 못 낸 채 `stop_reason: max_tokens` 로 끝났다. 블록이 `thinking` 하나뿐이라
#: "응답에 본문이 없습니다" 라는 엉뚱한 사유가 나왔다.
MAX_TOKENS = 16000

#: 입력 상한 (글자). 넘으면 **자르지 않고 그 사실을 말한다.**
#:
#: 실측 보드 하나가 펌웨어 12개 · 11만 자였다 (입력 5만 토큰). 조용히 잘라 넣으면
#: 모델이 못 본 파일에 대해 "문제 없음" 처럼 답하게 되고, 그게 제일 나쁘다.
#:
#: 15만 자면 실측 보드 6개 중 4개가 들어간다. 남는 둘은 **묻지 않고 그 사실을 말한다.**
#: 상한을 더 올리는 것보다 그게 낫다 — 이 기능은 옵트인이고, 한 번 부를 때마다
#: 입력 토큰이 그대로 비용이다.
MAX_INPUT_CHARS = 150_000

#: 한 번에 받을 후보 상한. 많이 받아 봐야 검증에서 대부분 떨어지고 비용만 는다.
MAX_CANDIDATES = 5

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        # `maxItems` 는 이 API 의 스키마가 안 받는다. 개수는 아래에서 코드가 자른다 —
        # 스키마로 못 막는 것을 프롬프트에만 맡기지 않는다.
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "why": {"type": "string"},
                    "citations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            # **칸의 뜻을 스키마에 적는다.** 프롬프트 산문에만 두면
                            # 모델이 `where` 에 `main.ino:13` 이나 `K1 -pad- (5V_BUS)` 처럼
                            # 합쳐서 낸다. 실제로 그래서 쓸 만한 후보를 여러 번 버렸다.
                            "properties": {
                                "kind": {
                                    "type": "string",
                                    "enum": ["firmware", "netlist"],
                                    "description": "firmware=소스 파일의 줄, netlist=회로도의 부품·핀",
                                },
                                "where": {
                                    "type": "string",
                                    "description": (
                                        "firmware 면 파일 이름만 (예: main.ino). "
                                        "netlist 면 부품기호만 (예: U1). "
                                        "줄 번호·핀 이름·설명을 여기 붙이지 마세요."
                                    ),
                                },
                                "what": {
                                    "type": ["string", "null"],
                                    "description": (
                                        "firmware 면 줄 번호만 (예: 13). "
                                        "netlist 면 핀 이름만 (예: D5). "
                                        "설명 문장을 쓰지 말고, 모르면 null 로 두세요."
                                    ),
                                },
                                "quote": {
                                    "type": ["string", "null"],
                                    "description": "그 자리의 원문 한 줄. 고치거나 요약하지 마세요 — 코드가 대조합니다.",
                                },
                            },
                            "required": ["kind", "where", "what", "quote"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["title", "why", "citations"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["candidates"],
    "additionalProperties": False,
}

SYSTEM = """당신은 임베디드 하드웨어 리뷰어입니다.

회로도 넷리스트와 펌웨어를 읽고, **아래 규칙들이 보지 못하는 위험**만 찾습니다.

지금 있는 규칙:
{rules}

이미 나온 발견:
{found}

지켜야 할 것:
- 위 규칙이 이미 보는 것은 **내지 마세요.** 새로운 모양만 냅니다.
- 모든 후보에는 **파일과 줄 번호, 또는 부품과 핀**을 답니다. 못 대면 내지 마세요.
- 인용문은 **원문 그대로** 적습니다. 요약하거나 고치지 마세요. 코드가 대조합니다.
- 확실하지 않으면 내지 마세요. **빈 목록이 정답인 경우가 많습니다.**
- 판정하지 마세요. 심각도를 매기지 마세요. 여기서 내는 것은 **후보**입니다.

근거 칸을 이렇게 채웁니다 —

    펌웨어:  {{"kind": "firmware", "where": "main.ino", "what": "13", "quote": "pinMode(RELAY_PIN, OUTPUT);"}}
    회로도:  {{"kind": "netlist",  "where": "K1", "what": "pad-", "quote": null}}

`where` 에 `main.ino:13` 처럼 합치거나 `K1 -pad- (5V_BUS)` 처럼 설명을 붙이면
**코드가 자리를 못 찾아 그 후보를 버립니다.**"""


def _rule_book(catalog_rules) -> str:
    return "\n".join(f"- {s.id}: {s.title}" for s in catalog_rules)


def _found(findings) -> str:
    if not findings:
        return "- (없음)"
    return "\n".join(f"- {f.rule} · {f.net or '—'}: {f.title}" for f in findings)


def propose(
    *,
    netlist_text: str,
    firmware_sources: "dict[str, str] | None",
    catalog_rules,
    findings,
    api_key: str | None = None,
) -> "tuple[list[Candidate], str | None]":
    """후보 목록과 (못 불렀으면) 그 사유.

    **부르지 않은 것과 못 부른 것은 다르다.** 키가 없으면 그렇게 말한다 (헌법 2-4).
    """
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return [], "ANTHROPIC_API_KEY 가 없어 모델을 부르지 않았습니다."

    try:
        import anthropic
    except ImportError:
        return [], "anthropic 패키지가 없어 모델을 부르지 않았습니다."

    parts = [f"## 넷리스트\n{netlist_text}"]
    for name, text in sorted((firmware_sources or {}).items()):
        parts.append(f"## 펌웨어 {name}\n{text}")
    body = "\n\n".join(parts)

    # **자르지 않는다.** 조용히 자르면 모델이 못 본 파일에 대해 답하게 된다.
    if len(body) > MAX_INPUT_CHARS:
        return [], (
            f"입력이 {len(body):,}자로 상한({MAX_INPUT_CHARS:,}자)을 넘어 묻지 않았습니다. "
            f"펌웨어 범위를 좁혀 다시 시도하세요 — 잘라서 물으면 모델이 못 본 파일에 대해 "
            f"답하게 됩니다."
        )

    try:
        msg = anthropic.Anthropic(api_key=key).messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM.format(rules=_rule_book(catalog_rules), found=_found(findings)),
            messages=[{"role": "user", "content": body}],
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        )
    except Exception as exc:  # noqa: BLE001 — 못 부른 것을 조용히 넘기지 않는다
        return [], f"{type(exc).__name__}: {exc}"

    # **첫 text 블록 하나가 곧 JSON 이다.** 여러 블록을 이어붙이면 JSON 이 깨진다 —
    # `datasheet/extract.py` 의 `_read_json` 과 같은 규칙이다.
    stop = getattr(msg, "stop_reason", None)
    if stop == "refusal":
        return [], "모델이 응답을 거절했습니다."
    if stop == "max_tokens":
        return [], f"모델이 출력 상한({MAX_TOKENS} 토큰)에 걸려 답을 끝맺지 못했습니다."
    block = next((b for b in msg.content if getattr(b, "type", None) == "text"), None)
    if block is None:
        return [], "모델 응답에 본문이 없습니다."
    try:
        data = json.loads(block.text)
    except json.JSONDecodeError as exc:
        return [], f"모델 응답을 JSON 으로 읽지 못했습니다 — {exc}"

    out: list[Candidate] = []
    for item in data.get("candidates", [])[:MAX_CANDIDATES]:
        out.append(
            Candidate(
                title=str(item.get("title") or "").strip(),
                why=str(item.get("why") or "").strip(),
                citations=tuple(
                    Citation(
                        kind=str(c.get("kind") or ""),
                        where=str(c.get("where") or ""),
                        what=None if c.get("what") is None else str(c.get("what")),
                        quote=None if c.get("quote") is None else str(c.get("quote")),
                    )
                    for c in item.get("citations", [])
                ),
            )
        )
    return out, None
