"""**LLM 이 낸 후보를 코드가 검증한다.** 이 모듈에는 네트워크도 LLM 도 없다.

## 무엇을 거르나

모델은 그럴듯한 문장을 잘 만든다. 그래서 **문장이 아니라 그 문장이 가리키는 자리**를 본다.
`datasheet/extract.py` 가 인용문을 원문과 대조하는 것과 같은 생각이다 —
지어낸 출처가 화면에 들어가는 것을 막을 수 있는 자리는 여기뿐이다.

    1. 자리가 실재하는가       없는 파일·줄·부품·핀을 가리키면 버린다
    2. 인용이 원문과 맞는가     그 줄에 그 내용이 정말 있는가
    3. 이미 보고 있는가        같은 자리에서 이미 발견이 났으면 후보가 아니다
    4. 말이 되는가            제목·이유가 비어 있으면 버린다

## 왜 이렇게까지 하나

이 기능은 **화면에 "우리가 못 봤을 수 있는 것" 이라고 적어 내보낸다.** 그 자리에
지어낸 것이 섞이면 도구 전체의 신뢰가 끝난다. 판정보다 오히려 더 엄해야 한다 —
판정은 근거가 붙어 있어서 사용자가 확인할 수 있지만, 후보는 "아직 모르는 것"이라
사용자가 대조할 기준이 없다.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import Candidate, Citation

#: 인용문이 원문과 같다고 볼 최소 조건. 공백만 봐준다 —
#: `datasheet/extract.py` 와 같은 규칙이다. 공백 말고는 안 봐준다.
NO_SPACE = str.maketrans("", "", " \t\r\n")

KIND_FIRMWARE = "firmware"
KIND_NETLIST = "netlist"


@dataclass(frozen=True)
class VerifyResult:
    kept: tuple[Candidate, ...]
    dropped: tuple[tuple[str, str], ...]


def _flat(text: str) -> str:
    return text.translate(NO_SPACE)


def _split_line(where: str, what: str | None) -> "tuple[str, str | None]":
    """`main.ino:13` 처럼 합쳐 온 것을 가른다.

    스키마로 칸을 나눠 줘도 모델은 곧잘 합쳐서 낸다. **형식이 어긋났다고 후보를 버리면
    안 된다** — 우리가 거르려는 것은 지어낸 내용이지 표기법이 아니다.
    실제로 이것 때문에 쓸 만한 후보 넷을 통째로 버렸다.
    """
    name = where.strip()
    if what not in (None, ""):
        return name, what
    head, sep, tail = name.rpartition(":")
    if sep and tail.strip().isdigit():
        return head.strip(), tail.strip()
    return name, what


def _firmware_ok(c: Citation, sources: "dict[str, str]") -> str | None:
    """펌웨어 자리를 확인한다. 문제가 있으면 사유, 없으면 None."""
    name, what = _split_line(c.where, c.what)
    hit = sources.get(name)
    if hit is None:
        # 경로가 다르게 올 수 있다 — 파일 이름으로 한 번 더 본다
        tail = name.rsplit("/", 1)[-1]
        matches = [v for k, v in sources.items() if k.rsplit("/", 1)[-1] == tail]
        if len(matches) != 1:
            return f"펌웨어에 {name} 파일이 없습니다"
        hit = matches[0]

    if what is None:
        return "줄 번호가 없습니다"
    try:
        line_no = int(str(what))
    except ValueError:
        return f"줄 번호가 숫자가 아닙니다 ({what})"

    lines = hit.splitlines()
    if not (1 <= line_no <= len(lines)):
        return f"{name} 는 {len(lines)}줄인데 {line_no}줄을 가리킵니다"

    if c.quote:
        # 지목한 줄 자체와, 그 앞뒤 한 줄까지 본다. 모델이 한 줄 어긋나게 세는 일이 흔하다.
        window = lines[max(0, line_no - 2) : line_no + 1]
        if _flat(c.quote) not in _flat("\n".join(window)):
            return f"{name}:{line_no} 에 인용한 내용이 없습니다"
    return None


def _netlist_ok(c: Citation, parts: "dict[str, set[str]]") -> str | None:
    """넷리스트 자리를 확인한다."""
    ref, pin = _split_pin(c.where, c.what)
    if ref not in parts:
        return f"회로도에 {ref} 부품이 없습니다"
    if pin and pin not in parts[ref]:
        return f"{ref} 에 {pin} 핀이 없습니다"
    return None


def _split_pin(where: str, what: str | None) -> "tuple[str, str | None]":
    """`U1.D5` 처럼 합쳐 온 것을 가른다. 펌웨어 쪽과 같은 이유다."""
    ref = where.strip()
    pin = (what or "").strip() or None
    if pin is None and "." in ref:
        head, _, tail = ref.partition(".")
        return head.strip(), tail.strip() or None
    return ref, pin


def verify(
    candidates: "list[Candidate]",
    *,
    firmware_sources: "dict[str, str] | None" = None,
    netlist_parts: "dict[str, set[str]] | None" = None,
    covered_places: "set[tuple[str, str]] | None" = None,
) -> VerifyResult:
    """후보를 하나씩 확인한다. **순수 함수다.**

    `covered_places` 는 기존 규칙이 이미 발견을 낸 자리 `(부품, 핀)` 집합이다.
    거기서 나온 후보는 새로운 것이 아니다.
    """
    sources = firmware_sources or {}
    parts = netlist_parts or {}
    covered = covered_places or set()

    kept: list[Candidate] = []
    dropped: list[tuple[str, str]] = []

    for c in candidates:
        title = (c.title or "").strip()
        if not title or not (c.why or "").strip():
            dropped.append((title or "(제목 없음)", "제목이나 이유가 비어 있습니다"))
            continue

        if not c.citations:
            dropped.append((title, "가리키는 자리가 없습니다 — 확인할 방법이 없습니다"))
            continue

        reason: str | None = None
        for cite in c.citations:
            if cite.kind == KIND_FIRMWARE:
                reason = _firmware_ok(cite, sources)
            elif cite.kind == KIND_NETLIST:
                reason = _netlist_ok(cite, parts)
            else:
                reason = f"모르는 근거 종류입니다 ({cite.kind})"
            if reason:
                break
        if reason:
            dropped.append((title, reason))
            continue

        # 이미 규칙이 보고 있는 자리인가
        here = {
            (cite.where.strip(), (cite.what or "").strip())
            for cite in c.citations
            if cite.kind == KIND_NETLIST
        }
        overlap = here & covered
        if overlap:
            ref, pin = sorted(overlap)[0]
            dropped.append((title, f"{ref}.{pin} 는 이미 기존 규칙이 보고 있습니다"))
            continue

        kept.append(c)

    return VerifyResult(kept=tuple(kept), dropped=tuple(dropped))
