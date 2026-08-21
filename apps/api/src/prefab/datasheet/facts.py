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

#: `output_type` 이 가질 수 있는 값. **문자열을 손으로 적지 않는다** —
#: 규칙이 `"open-drain"` 을 오타로 쓰면 조용히 아무것도 해제 안 된다.
OPEN_DRAIN = "open-drain"
PUSH_PULL = "push-pull"

#: 사람이 쓰는 표기를 위 상수로 옮긴다. **LLM 이 읽고 코드가 정규화한다.**
#:
#: 데이터시트는 `Open Drain Charge Status Output` 처럼 문장으로 적는다. 추출기는
#: 그걸 그대로 실어 오는데(자유 텍스트라 스키마가 못 막는다), 규칙은 상수와 비교한다.
#: 그러면 **사실이 DB 에 있는데도 아무것도 해제되지 않는다** — 조용한 실패다.
#:
#: `open collector` 도 같이 본다. 전기적으로 우리 판정에는 같은 뜻이다.
_OUTPUT_TYPE_HINTS: "tuple[tuple[str, tuple[str, ...]], ...]" = (
    (OPEN_DRAIN, ("open drain", "open-drain", "opendrain", "open collector",
                  "open-collector", "오픈드레인", "오픈 드레인")),
    (PUSH_PULL, ("push pull", "push-pull", "pushpull", "푸시풀", "totem pole")),
)


def normalize_output_type(value: object) -> object:
    """`Open Drain Charge Status Output` → `open-drain`. 애매하면 **그대로 둔다.**

    둘 다 나오면 손대지 않는다 — `핀6은 오픈드레인, CE 는 푸시풀` 같은 문장을
    한쪽으로 뭉개면 없는 사실을 만드는 것이다 (헌법 2-2).
    """
    if not isinstance(value, str):
        return value
    low = value.lower()
    hit = [canon for canon, words in _OUTPUT_TYPE_HINTS if any(w in low for w in words)]
    return hit[0] if len(hit) == 1 else value
IO_LEVEL = "io_level"                  #: 모듈 IO 가 도는 로직 레벨
INPUT_PULLUP_TO = "input_pullup_to"    #: 입력 핀이 내부에서 어디로 풀업되는가

#: `input_pullup_to` 가 이 값이면 **확인 결과 풀업이 없다**는 뜻이다.
#: `value: null` 은 "모른다" 이고 이건 "없다" 다. 둘을 섞으면 모르는 것을 안다고 말하게 된다.
NO_PULLUP = "none"

#: 보드가 칩에서 물려받는 항목.
#:
#: 핀의 전기 특성은 **칩이 정하고 보드가 바꾸지 못한다.** GPIO 가 몇 V 를 견디는지는
#: 브레이크아웃 보드를 거쳐도 그대로다.
#:
#: **`vcc_nominal` 은 일부러 뺐다.** 보드에는 레귤레이터가 있다 — XIAO ESP32C6 은
#: USB 5V 를 받아 칩에 3.3V 를 준다. 칩의 3.3V 를 보드 공급 전압이라고 하면
#: 틀린 값이 되고, 그 틀린 값으로 R11·R12 가 판정한다.
CHIP_INHERITED: tuple[str, ...] = (
    VIH_MIN,
    VIL_MAX,
    VOH_MAX,
    VOL_MAX,
    VIN_ABSOLUTE_MAX,
    IO_LEVEL,
    OUTPUT_TYPE,
    INPUT_PULLUP_TO,
)

#: 사용자에게 보여줄 이름. "voh_max 를 못 읽었습니다"는 비전공자가 못 읽는다.
FIELD_LABELS: dict[str, str] = {
    VOH_MAX: "출력 하이 전압(Voh)",
    VOL_MAX: "출력 로우 전압(Vol)",
    VIH_MIN: "입력 하이 문턱(Vih)",
    VIL_MAX: "입력 로우 문턱(Vil)",
    VCC_NOMINAL: "정격 공급 전압",
    VIN_ABSOLUTE_MAX: "입력 절대 최대 전압",
    OUTPUT_TYPE: "출력 단 형식",
    IO_LEVEL: "IO 로직 레벨",
    INPUT_PULLUP_TO: "입력 내부 풀업",
}


def label(field: str) -> str:
    return FIELD_LABELS.get(field, field)


#: 확신도. `none` 은 "값을 못 찾았다"이고 실패가 아니라 정상적인 결과다.
CONF_HIGH = "high"
CONF_MEDIUM = "medium"
CONF_LOW = "low"
CONF_NONE = "none"

#: 출처 등급. 공식이 아니면 규칙이 판정을 낮출 수 있어야 한다.
#: 데이터시트가 아니라 **실물을 재서** 얻은 값. 쪽 번호 대신 측정 기록이 출처다.
#: 데이터시트가 없거나 그 항목을 안 싣는 부품이 있다 — 그때 남는 길이 측정이다.
TIER_MEASURED = "measured"

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
    def measured(self) -> bool:
        """데이터시트가 아니라 실물을 재서 얻은 값인가."""
        return self.source_tier == TIER_MEASURED

    @property
    def has_provenance(self) -> bool:
        """이 값이 어디서 왔는지 말할 수 있는가.

        데이터시트면 어느 표 몇 쪽인지, **실측이면 무엇을 어떻게 쟀는지**다.
        측정도 출처다 — 쪽 번호가 아니라 측정 기록이 그 자리를 채운다.
        어느 쪽이든 빈손이면 값이 아니다.
        """
        if self.measured:
            return bool(self.quote)
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
        if self.measured:
            return " · ".join(b for b in ("실측", self.table) if b)
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
