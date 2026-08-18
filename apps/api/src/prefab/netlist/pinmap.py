"""패드 하나하나에 실크 라벨과 GPIO 번호를 붙인다.

IPC-D-356 은 핀 이름을 4자에서 자른다. 그래서 U1 의 물리적으로 다른 핀이
`SDIO` 하나로 뭉친다 (D3 · D4 · D5). 이름으로는 못 푼다.

**기하가 이름이 잃어버린 것을 복원한다.** 헤더는 등간격 두 열이고, Y 내림차순이
실크 순서다. 그 순서로 읽은 절단 이름 나열이 모듈 표의 서명과 **전부** 맞을 때만
라벨을 붙인다. 하나라도 어긋나면 붙이지 않는다 — 추측해서 GPIO 번호를 지어내면
그 위에 올라가는 R7 · R8 이 통째로 거짓말이 된다.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..chips import MODULES, ModulePinout
from .d356 import Netlist, Pad

#: 같은 헤더 열로 볼 X 좌표 허용 오차 (inch). 0.1 inch 피치의 절반보다 작게 잡는다.
COLUMN_TOL_INCH = 0.02

#: 헤더 열로 인정할 최소 패드 수. 두세 개짜리 우연한 정렬을 걸러낸다.
MIN_COLUMN_PADS = 4


@dataclass(frozen=True)
class PadIdentity:
    """패드 하나의 확정된 신원."""

    ref: str
    pin: str
    x: float | None
    y: float | None
    silk: str
    gpio: int | None
    module: str

    @property
    def key(self) -> tuple:
        return (self.ref, self.pin, self.x, self.y)


class PinMap:
    """넷리스트 전체의 패드 신원. 못 푼 패드는 그냥 없다."""

    def __init__(self, identities: "list[PadIdentity]", modules_matched: "dict[str, str]") -> None:
        self._by_key = {i.key: i for i in identities}
        #: refdes → 매칭된 모듈 id
        self.modules_matched = modules_matched

    def __len__(self) -> int:
        return len(self._by_key)

    def __bool__(self) -> bool:
        return bool(self._by_key)

    def of(self, pad: Pad) -> PadIdentity | None:
        return self._by_key.get((pad.ref, pad.pin, pad.x, pad.y))

    def find(
        self, *, silk: str | None = None, gpio: int | None = None, ref: str | None = None
    ) -> PadIdentity | None:
        """실크 라벨이나 GPIO 번호로 패드를 찾는다. 둘 다 주면 실크가 우선한다."""
        for i in self._by_key.values():
            if ref is not None and i.ref != ref:
                continue
            if silk is not None and i.silk == silk:
                return i
            if silk is None and gpio is not None and i.gpio == gpio:
                return i
        if silk is not None and gpio is not None:
            return self.find(gpio=gpio, ref=ref)
        return None

    def gpio_pads(self) -> "list[PadIdentity]":
        """GPIO 번호가 있는 패드만. 전원·접지 헤더 핀은 빠진다."""
        return sorted(
            (i for i in self._by_key.values() if i.gpio is not None),
            key=lambda i: i.gpio,
        )

    def all(self) -> "list[PadIdentity]":
        return list(self._by_key.values())


def _columns(pads: "list[Pad]") -> "list[list[Pad]]":
    """X 좌표로 패드를 열로 묶고, 각 열을 Y 내림차순으로 정렬한다."""
    buckets: "list[list[Pad]]" = []
    for pad in pads:
        if pad.x is None or pad.y is None:
            continue
        for bucket in buckets:
            if abs(bucket[0].x - pad.x) < COLUMN_TOL_INCH:
                bucket.append(pad)
                break
        else:
            buckets.append([pad])
    return [sorted(b, key=lambda p: -p.y) for b in buckets if len(b) >= MIN_COLUMN_PADS]


def _match_part(ref: str, pads: "list[Pad]", module: ModulePinout) -> "list[PadIdentity]":
    """한 부품의 패드를 모듈 표에 맞춰본다. 열 서명이 전부 맞을 때만 라벨을 붙인다."""
    found: "list[PadIdentity]" = []
    used: "set[int]" = set()

    for column in _columns(pads):
        tokens = tuple(p.pin for p in column)
        for idx in range(len(module.columns)):
            if idx in used:
                continue
            if tokens != module.signature(idx):
                continue
            used.add(idx)
            for pad, header in zip(column, module.columns[idx]):
                found.append(
                    PadIdentity(
                        ref=ref,
                        pin=pad.pin,
                        x=pad.x,
                        y=pad.y,
                        silk=header.silk,
                        gpio=header.gpio,
                        module=module.id,
                    )
                )
            break

    # 열 하나만 맞고 나머지가 안 맞으면 보드가 다른 것이다. 절반만 믿지 않는다.
    if len(used) != len(module.columns):
        return []
    return found


def resolve(netlist: Netlist) -> PinMap:
    """넷리스트에서 알려진 모듈을 찾아 패드마다 실크·GPIO 를 확정한다."""
    pads_by_ref: "dict[str, list[Pad]]" = {}
    for pads in netlist.nets.values():
        for pad in pads:
            if pad.is_via:
                continue
            pads_by_ref.setdefault(pad.ref, []).append(pad)

    identities: "list[PadIdentity]" = []
    matched: "dict[str, str]" = {}

    for ref, pads in pads_by_ref.items():
        for module in MODULES.values():
            found = _match_part(ref, pads, module)
            if found:
                identities.extend(found)
                matched[ref] = module.id
                break

    return PinMap(identities, matched)
