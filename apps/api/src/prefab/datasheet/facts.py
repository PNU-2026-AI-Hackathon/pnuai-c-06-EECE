"""부품 사실(fact) — 순수 자료형.

**여기에 IO 가 없다.** 규칙 함수는 순수 함수라서 DB 를 직접 못 본다 (CLAUDE.md 2-1).
그래서 조회는 바깥(`store.py`)에서 하고, 그 **결과만** `Context.datasheet` 로 들어온다.

`.claude/skills/prefab-datasheet` 5단계 스키마를 그대로 옮긴 것이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

#: 규칙과 추출기가 같은 이름을 쓰도록 고정한다. 문자열을 흩뿌리지 않는다.
VOH_MAX = "voh_max"                    #: 출력 High 전압 최대
VOL_MAX = "vol_max"                    #: 출력 Low 전압 최대
VIH_MIN = "vih_min"                    #: 입력 High 문턱 최소
VIL_MAX = "vil_max"                    #: 입력 Low 문턱 최대
VCC_NOMINAL = "vcc_nominal"            #: 정격 공급 전압
VIN_ABSOLUTE_MAX = "vin_absolute_max"  #: 입력 절대 최대 (넘으면 파손)
OUTPUT_TYPE = "output_type"            #: push-pull / open-drain
INPUT_PULLUP_TO = "input_pullup_to"    #: 입력 핀이 내부에서 어디로 풀업되는가

#: 확신도. `none` 은 "값을 못 찾았다"이고 실패가 아니라 정상적인 결과다.
CONF_HIGH = "high"
CONF_MEDIUM = "medium"
CONF_LOW = "low"
CONF_NONE = "none"

#: 출처 등급. 공식이 아니면 규칙이 판정을 낮출 수 있어야 한다.
TIER_OFFICIAL = "official"
TIER_DISTRIBUTOR = "distributor"
TIER_UNOFFICIAL = "unofficial"

#: 판정에 쓸 수 있는 확신도. low 로 PASS 를 내지 않는다 (스킬 "하지 말 것").
_TRUSTED = (CONF_HIGH, CONF_MEDIUM)


@dataclass(frozen=True)
class Fact:
    """데이터시트에서 읽은 값 하나. **출처가 없으면 값이 아니다.**"""

    mpn: str
    field: str
    value: float | str | None
    unit: str | None = None
    table: str | None = None
    page: int | None = None
    quote: str | None = None
    confidence: str = CONF_NONE
    #: 값이 없을 때 왜 없는지. `value is None` 이면 반드시 있어야 한다.
    reason: str | None = None
    source_url: str | None = None
    source_tier: str = TIER_UNOFFICIAL

    @property
    def has_provenance(self) -> bool:
        """어느 표 몇 쪽에서 읽었는지 말할 수 있는가."""
        return self.page is not None and bool(self.quote)

    @property
    def usable(self) -> bool:
        """이 값으로 판정을 내려도 되는가.

        값이 있고 · 출처가 있고 · 확신도가 낮지 않아야 한다.
        하나라도 빠지면 규칙은 `UNRESOLVED` 로 남겨야 한다.
        """
        return (
            self.value is not None
            and self.has_provenance
            and self.confidence in _TRUSTED
        )

    def cite(self) -> str:
        """사용자에게 보여줄 출처 한 줄."""
        bits = [b for b in (self.table, f"p.{self.page}" if self.page else None) if b]
        return " · ".join(bits) or "출처 없음"


class FactSet:
    """한 검사에서 손에 든 사실 전부. 규칙이 이것만 본다."""

    def __init__(self, facts: Iterable[Fact] = ()) -> None:
        self._by_mpn: dict[str, dict[str, Fact]] = {}
        for f in facts:
            self._by_mpn.setdefault(f.mpn, {})[f.field] = f

    def __len__(self) -> int:
        return sum(len(v) for v in self._by_mpn.values())

    @property
    def mpns(self) -> list[str]:
        return sorted(self._by_mpn)

    def get(self, mpn: str, field: str) -> Fact | None:
        return self._by_mpn.get(mpn, {}).get(field)

    def usable(self, mpn: str, field: str) -> Fact | None:
        """판정에 쓸 수 있는 사실만 돌려준다. 없으면 None → 규칙은 UNRESOLVED."""
        f = self.get(mpn, field)
        return f if f is not None and f.usable else None

    def facts_of(self, mpn: str) -> list[Fact]:
        return list(self._by_mpn.get(mpn, {}).values())

    def to_dict(self) -> dict[str, Any]:
        return {"mpns": self.mpns, "facts": len(self)}
