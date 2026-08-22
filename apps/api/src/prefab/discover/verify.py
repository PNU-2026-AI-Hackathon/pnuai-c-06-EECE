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


def _line_no(what: str | None, suffix: str | None) -> "int | None":
    for v in (what, suffix):
        if v is None:
            continue
        s = str(v).strip()
        if s.isdigit():
            return int(s)
    return None


def _find_source(where: str, sources: "dict[str, str]") -> "tuple[str, str, str | None] | None":
    """`where` 로 소스를 찾는다. `(이름, 본문, 떼어낸 줄 접미)` 또는 None.

    **찾아보고 안 되면 갈라 본다.** 형식을 미리 단정하지 않는다 — 모델은
    `main.ino` 로도, `main.ino:13` 으로도, `src/main.ino` 로도 낸다.
    한 번에 맞히려 하면 그중 하나에서 조용히 틀린다.
    """
    def by_name(name: str) -> "tuple[str, str] | None":
        if name in sources:
            return name, sources[name]
        tail = name.rsplit("/", 1)[-1]
        hits = [(k, v) for k, v in sources.items() if k.rsplit("/", 1)[-1] == tail]
        return hits[0] if len(hits) == 1 else None

    name = where.strip()
    hit = by_name(name)
    if hit:
        return hit[0], hit[1], None

    # `main.ino:13` 처럼 줄이 붙어 온 경우. **`what` 이 따로 와도 여기로 온다** —
    # 모델은 둘 다 채우는 일이 흔한데, 그걸 안 보고 이름만 찾다가 쓸 만한 후보를 버렸다.
    head, sep, tail = name.rpartition(":")
    if sep and tail.strip().isdigit():
        hit = by_name(head.strip())
        if hit:
            return hit[0], hit[1], tail.strip()
    return None


def _firmware_ok(c: Citation, sources: "dict[str, str]") -> str | None:
    """펌웨어 자리를 확인한다. 문제가 있으면 사유, 없으면 None."""
    found = _find_source(c.where, sources)
    if found is None:
        return f"펌웨어에 {c.where.strip()} 파일이 없습니다"
    name, body, suffix = found

    line_no = _line_no(c.what, suffix)
    if line_no is None:
        return "줄 번호가 없습니다"

    lines = body.splitlines()
    if not (1 <= line_no <= len(lines)):
        return f"{name} 는 {len(lines)}줄인데 {line_no}줄을 가리킵니다"

    if c.quote:
        # 지목한 줄과 그 앞뒤 한 줄까지 본다. 모델이 한 줄 어긋나게 세는 일이 흔하다.
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
    """부품기호와 핀을 가른다. **모델은 설명까지 붙여 낸다.**

    실제로 이런 것이 왔다 — `K1 -pad- (5V_BUS, 접점 COM)`.
    부품기호는 맨 앞 토큰이고, 나머지는 사람이 읽으라고 붙인 말이다.
    """
    raw = where.strip()
    pin = (what or "").strip() or None

    ref = raw.split()[0] if raw.split() else raw
    # `U1.D5` · `U1-D5` 둘 다 온다. 구분자만 봐준다
    if pin is None:
        for sep in (".", "-"):
            head, found, tail = ref.partition(sep)
            if found and tail.strip():
                return head.strip(), tail.strip()

    # **`what` 에 설명 문장이 오면 핀 이름으로 안 본다.**
    # `"릴레이 제어 입력이 _IN_ACTIVE_LOW 네트"` 같은 것을 핀 이름과 대조하면
    # 멀쩡한 후보가 "그런 핀이 없습니다" 로 떨어진다. **확인할 수 있는 것만 확인한다** —
    # 부품이 실재하는지는 그대로 본다.
    if pin and (" " in pin or len(pin) > 24):
        pin = None
    return ref.strip(), pin


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
