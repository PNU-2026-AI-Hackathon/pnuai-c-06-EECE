"""토폴로지가 던진 질문에 데이터시트가 답하는 자리.

규칙은 넷리스트만으로 플래그를 세운다. 그 플래그를 **지우기 위해서만** 사실을 본다
(CLAUDE.md 2-1). 여기는 그 조회를 한 군데로 모은 곳이고, **여전히 순수 함수**다 —
DB 는 러너가 이미 읽어서 `ctx.datasheet` 에 넣어 놨다.

이 파일의 진짜 일은 답을 찾는 것보다 **못 찾았을 때 무엇이 있으면 풀리는지 말하는 것**이다.
"미식별 — BOM 필요"는 BOM 을 이미 낸 사람에게는 거짓말이다.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..datasheet.facts import IO_LEVEL, VOH_MAX, Fact, FactSet, label
from ..types import Context, Evidence


#: 출력이 어디까지 올라가는지 말해 주는 항목들. 앞의 것이 더 직접적인 규격이다.
#:
#: `voh_max` 가 정석이지만 **모듈 데이터시트는 그 규격을 잘 안 준다.**
#: 대신 "IO 레벨 3.3V" 라고 적는다. 그것도 출력 상한을 말해 준다 —
#: IO 레일이 3.3V 인데 그 핀의 출력이 5V 로 올라갈 수는 없다.
#: 실측에서 나온 문제다: `HLK-LD2410C` 매뉴얼에 Voh 규격이 없어서
#: 사람이 "IO 레벨 3.3V" 를 `voh_max` 라고 적었고, 그건 없는 규격을
#: 있다고 말한 것이었다. 항목을 나누고 규칙이 둘 다 보게 한다.
OUTPUT_BOUND_FIELDS = (VOH_MAX, IO_LEVEL)


@dataclass(frozen=True)
class Answer:
    """데이터시트에 물어본 결과."""

    #: 판정에 쓸 수 있는 사실. 없으면 None 이고, 그때 `missing` 이 채워진다.
    fact: Fact | None = None
    mpn: str | None = None
    #: 왜 아직 답을 못 얻었는지. **무엇을 하면 풀리는지까지 적는다.**
    missing: str | None = None

    @property
    def answered(self) -> bool:
        return self.fact is not None

    def evidence(self) -> Evidence | None:
        """화면에 붙일 출처. 사실이 없으면 붙일 것도 없다."""
        f = self.fact
        if f is None or f.page is None or not f.quote:
            return None
        return Evidence.datasheet(
            mpn=f.mpn, table=f.table or "", page=f.page, quote=f.quote
        )


def ask(
    ctx: Context,
    ref: str,
    field: str,
    *,
    what: str | None = None,
    resolve: bool = True,
) -> Answer:
    """부품기호 하나에 대해 항목 하나를 묻는다.

    부품기호(`K1`)는 BOM 을 거쳐야 부품번호가 되고, 부품번호가 있어야 사실을 찾는다.
    끊긴 자리마다 다른 말을 해야 사용자가 다음에 뭘 할지 안다.

    `resolve=False` 는 **답이 있어도 쓰지 않는다.** 질문이 맞는지 자체가 불확실할 때
    쓴다 — 예를 들어 그 부품이 이 네트를 구동하는지도 모르면 출력 전압은
    물어볼 값이 아니다. 그때도 `missing` 은 채워서, 다음에 뭘 할지는 말해 준다.
    `what` 은 그 경우 사용자에게 보여줄 이름을 바꾸는 용도다.
    """
    what = what or label(field)

    bom = ctx.bom
    if bom is None:
        return Answer(missing=f"{ref} 미식별 — BOM 을 제출하면 {what}을 확인합니다")

    mpn = bom.mpn_of(ref)
    if not mpn:
        return Answer(
            missing=f"{ref} 이 BOM 에 없거나 부품번호가 비어 있습니다 — 부품번호가 있어야 {what}을 찾습니다"
        )

    if not resolve:
        return Answer(mpn=mpn, missing=f"{mpn} — {what}을 확인해야 합니다")

    facts: FactSet | None = ctx.datasheet
    if facts is None or facts.get(mpn, field) is None:
        return Answer(
            mpn=mpn,
            missing=f"{mpn} 의 데이터시트를 아직 읽지 않았습니다 — {what}이 필요합니다",
        )

    found = facts.get(mpn, field)
    if found.usable:
        return Answer(fact=found, mpn=mpn)

    return Answer(mpn=mpn, missing=f"{mpn} — {_why_unusable(found, what)}")


def ask_output_bound(
    ctx: Context, ref: str, *, resolve: bool = True, what: str | None = None
) -> Answer:
    """출력이 어디까지 올라가는지 묻는다. `OUTPUT_BOUND_FIELDS` 를 순서대로 본다.

    하나라도 답하면 그걸 쓴다. 아무것도 못 찾으면 **가장 직접적인 항목의
    미결 사유**를 돌려준다 — 사용자에게 "Voh 를 주세요"가 "IO 레벨을 주세요"보다
    쓸모 있는 안내다.
    """
    first: Answer | None = None
    for field in OUTPUT_BOUND_FIELDS:
        answer = ask(ctx, ref, field, resolve=resolve, what=what)
        if answer.answered:
            return answer
        if first is None:
            first = answer
    assert first is not None  # OUTPUT_BOUND_FIELDS 는 비어 있지 않다
    return first


def _why_unusable(f: Fact, what: str) -> str:
    """왜 이 값으로 판정하지 않는지. 값이 있어도 못 쓰는 경우가 있다."""
    if f.value is None:
        return f"데이터시트에 {what}이 없습니다 ({f.reason or '이유 미기록'})"
    if not f.has_provenance:
        return f"{what} 값에 출처가 없어 판정에 쓰지 않습니다"
    return f"{what} 값의 확신도가 낮아 판정에 쓰지 않습니다 ({f.cite()})"


def number(answer: Answer) -> float | None:
    """전압처럼 숫자여야 비교가 되는 항목. 문자열이 오면 비교하지 않는다."""
    f = answer.fact
    if f is None or not isinstance(f.value, (int, float)):
        return None
    return float(f.value)
