"""LLM 베이스라인 — **같은 보드, 같은 입력, 같은 규칙 목록**으로 모델에게 물어본다.

*"그냥 GPT 한테 주면 되는 거 아닌가요"* 에 댈 숫자를 만드는 자리다.
2026-08-20 에 실보드 6개로 한 번 쟀고(그때 우리가 졌다), 이 스크립트는
**홀드아웃 보드**에 같은 것을 다시 하기 위한 것이다.

## 공정하게 재기 위해 지킨 것

- 엔진과 **똑같은 입력**을 준다 (넷리스트 원문 + 펌웨어 원문)
- **규칙 목록을 준다.** 안 주면 무엇을 찾아야 하는지 모르는 채로 재는 것이라 불공정하다
- **정답은 안 준다.** 우리 엔진이 뭘 찾았는지도 안 알려준다
- 입력이 상한을 넘으면 **자르지 않고 그 보드를 건너뛴다.** 조용히 자르면 모델이
  못 본 파일에 대해 "문제 없음" 처럼 답하고, 그 숫자는 거짓말이 된다

    python scripts/llm_baseline.py --boards /tmp/holdout --out /tmp/llm.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prefab import catalog  # noqa: E402
from prefab.__main__ import _load_env  # noqa: E402

MODEL = os.getenv("PREFAB_BASELINE_MODEL", "claude-sonnet-5")
#: 출력 상한. 낮게 두면 모델이 생각에만 다 쓰고 답을 못 낸다 —
#: 그러면 블록이 thinking 하나뿐이라 "응답에 본문이 없습니다" 라는 엉뚱한 사유가 나온다.
#: `discover/propose.py` 가 같은 자리에서 데였다.
MAX_TOKENS = 16000
#: 입력 상한 (글자). 넷리스트에서 라이브러리 메타데이터를 뺀 뒤 재는 값이다.
MAX_INPUT_CHARS = 260_000

#: 엔진이 안 보는 부분. 빼도 정보가 줄지 않고, 그대로 두면 입력의 대부분이 이것이다.
UNUSED_XML = re.compile(r"<libparts>.*?</libparts>|<libraries>.*?</libraries>", re.S)

SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule": {"type": "string"},
                    "net": {"type": ["string", "null"]},
                    "severity": {"type": "string", "enum": ["CRITICAL", "WARNING"]},
                    "claim": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": ["rule", "net", "severity", "claim", "evidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}

SYSTEM = """\
당신은 PCB 회로도와 펌웨어를 대조해 **보드를 발주하기 전에** 잡아야 할 결함을 찾습니다.

아래 규칙 목록이 이 검사가 보는 범위입니다. 목록에 없는 것도 찾았으면 `rule` 을 `"NEW"` 로 두세요.

**가장 중요한 것: 확실하지 않으면 말하지 마세요.**
회로도만으로 알 수 없는 것(부품의 실제 정격, 커넥터 뒤에 무엇이 붙는지, 핀 방향)을
추측해서 결함이라고 하면 안 됩니다. 잘못된 경고 하나가 검사 도구를 꺼지게 만듭니다.

- `evidence` 에는 **넷리스트나 코드 원문을 그대로** 옮기세요. 없는 줄을 지어내면 안 됩니다
- 정상 설계를 결함이라고 하지 마세요. 레벨 시프터·풀업·분압은 **해법**이지 문제가 아닙니다
- 결함이 없으면 빈 목록을 내세요. 억지로 채우지 마세요
"""


def rule_list() -> str:
    return "\n".join(
        f"- {s.id} ({s.tier}) {s.title}" for s in catalog.CATALOG
    )


def build_prompt(
    board: str, netlist: str, firmware: dict[str, str], omitted: list[str]
) -> str:
    """엔진이 보는 것과 같은 것을 준다.

    `<libparts>`·`<libraries>` 는 뺀다 — 엔진도 안 보고, 그대로 두면 입력의 대부분이
    그것이다. **정보를 줄이는 게 아니라 같은 정보를 작게 주는 것이다.**
    """
    parts = [
        f"# 보드: {board}\n", "## 검사 규칙\n", rule_list(),
        "\n\n## 회로도 넷리스트\n", UNUSED_XML.sub("", netlist),
    ]
    if firmware:
        parts.append("\n\n## 펌웨어\n")
        for name, text in firmware.items():
            parts.append(f"\n### {name}\n```\n{text}\n```\n")
    if omitted:
        # 못 준 파일을 말해 준다. 모르는 채로 "문제 없음" 이라고 답하면 안 된다.
        parts.append(
            f"\n\n## 넣지 못한 펌웨어 파일 {len(omitted)}개\n"
            + "\n".join(f"- {n}" for n in omitted[:40])
            + "\n\n이 파일들은 보지 못했습니다. 이 파일이 근거여야 하는 결함은 말하지 마세요.\n"
        )
    return "".join(parts)


def ask(client, prompt: str, *, thinking: bool = True) -> dict:
    """`thinking=False` 면 적응형 사고를 끈다.

    **끄는 이유는 속도가 아니라 재기 위해서다.** 사고를 켜면 큰 보드에서 출력 상한을
    생각에 다 써서 답을 못 내고, 그 보드가 통째로 숫자에서 빠진다 — 처음 돌렸을 때
    10개 중 2개가 그랬다. 못 잰 보드는 "발견 0건" 이 아니라 **모르는 보드**다.

    Sonnet 5 에는 API 의 fast mode(`speed="fast"`)가 없다 — 그건 Opus 5·4.8 전용이다.
    여기서 할 수 있는 빠른 쪽은 이것뿐이고, **조건이 달라졌으니 따로 적어서 비교한다.**
    """
    extra = {} if thinking else {"thinking": {"type": "disabled"}}
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
        **extra,
    )
    if getattr(response, "stop_reason", None) == "refusal":
        raise RuntimeError("모델이 거절했습니다")
    for block in response.content:
        if getattr(block, "type", None) == "text":
            out = json.loads(block.text)
            out["_usage"] = {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
            }
            return out
    raise RuntimeError("응답에 본문이 없습니다")


def main() -> int:
    ap = argparse.ArgumentParser(description="홀드아웃 보드에 LLM 베이스라인을 돌린다")
    ap.add_argument("--boards", required=True, help="holdout.py 가 쓴 작업 폴더")
    ap.add_argument("--engine", help="holdout.py --json 결과 (보드 목록을 여기서 읽는다)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-thinking", action="store_true",
                    help="적응형 사고를 끈다 (큰 보드에서 답을 못 내는 것을 막는다)")
    args = ap.parse_args()

    _load_env(Path.cwd())
    import anthropic

    client = anthropic.Anthropic()
    work = Path(args.boards)
    engine = json.loads(Path(args.engine or work / "before.json").read_text(encoding="utf-8"))

    # holdout.py 가 쓴 것과 **같은 방법**으로 펌웨어를 모은다. 다르면 비교가 안 된다.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from holdout import firmware_of

    results, spend = [], {"input": 0, "output": 0}
    for board in engine["boards"]:
        name = board["board"]
        repo_dir = work / board["repo"].split("/")[-1]
        # holdout.py 가 stem 을 쓰므로 name 에 이미 ".net" 이 남아 있다.
        net_path = work / "nets" / f"{name}.xml"
        if not net_path.exists():
            print(f"?? {name}: 넷리스트가 없습니다", file=sys.stderr)
            continue

        netlist = net_path.read_text(encoding="utf-8", errors="replace")
        firmware, omitted = firmware_of(repo_dir) if repo_dir.exists() else ({}, [])
        prompt = build_prompt(name, netlist, firmware, omitted)

        if len(prompt) > MAX_INPUT_CHARS:
            # 자르지 않는다. 못 본 것을 "문제 없음" 이라고 답하게 만드는 것이 제일 나쁘다.
            print(f"-- {name:28} 입력 {len(prompt):,}자 — 상한 초과, 건너뜀", file=sys.stderr)
            results.append({"board": name, "repo": board["repo"], "skipped": "입력 상한 초과",
                            "findings": []})
            continue

        try:
            got = ask(client, prompt, thinking=not args.no_thinking)
        except Exception as exc:
            print(f"?? {name}: {type(exc).__name__}: {str(exc)[:120]}", file=sys.stderr)
            results.append({"board": name, "repo": board["repo"],
                            "skipped": f"{type(exc).__name__}", "findings": []})
            continue

        use = got.pop("_usage")
        spend["input"] += use["input"]
        spend["output"] += use["output"]
        results.append({"board": name, "repo": board["repo"], "findings": got["findings"]})
        print(f"OK {name:28} LLM 발견 {len(got['findings']):2}건 "
              f"(엔진 {len(board['findings'])}건) · 입력 {use['input']:,} 토큰")

    llm_total = sum(len(r["findings"]) for r in results)
    eng_total = sum(len(b["findings"]) for b in engine["boards"])
    skipped = [r["board"] for r in results if r.get("skipped")]

    print("=" * 66)
    mode = "사고 끔" if args.no_thinking else "적응형 사고"
    print(f"보드 {len(results)}개 · 엔진 {eng_total}건 · LLM {llm_total}건 ({MODEL} · {mode})")
    if skipped:
        print(f"LLM 이 못 본 보드 {len(skipped)}개: {', '.join(skipped)} — 숫자에서 빠져 있습니다")
    cost = spend["input"] / 1e6 * 2 + spend["output"] / 1e6 * 10  # Sonnet 5 도입가
    print(f"토큰 입력 {spend['input']:,} · 출력 {spend['output']:,} · 약 ${cost:.2f}")
    print("=" * 66)

    Path(args.out).write_text(
        json.dumps({"model": MODEL, "boards": results, "usage": spend}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
