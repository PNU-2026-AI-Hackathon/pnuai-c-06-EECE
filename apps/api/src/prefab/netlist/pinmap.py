"""패드 하나하나에 실크 라벨과 GPIO 번호를 붙인다.

IPC-D-356 은 핀 이름을 4자에서 자른다. 그래서 U1 의 물리적으로 다른 핀이
`SDIO` 하나로 뭉친다 (D3 · D4 · D5). 이름으로는 못 푼다.

**기하가 이름이 잃어버린 것을 복원한다.** 헤더는 등간격 두 열이고, Y 내림차순이
실크 순서다. 그 순서로 읽은 절단 이름 나열이 모듈 표의 서명과 **전부** 맞을 때만
라벨을 붙인다. 하나라도 어긋나면 붙이지 않는다 — 추측해서 GPIO 번호를 지어내면
그 위에 올라가는 R7 · R8 이 통째로 거짓말이 된다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..chips import MODULES, ModulePinout
from .d356 import Netlist, Pad

#: 같은 헤더 열로 볼 X 좌표 허용 오차 (inch). 0.1 inch 피치의 절반보다 작게 잡는다.
#: 맨칩 패드 이름에서 GPIO 번호를 읽는다.
#:
#: 모듈 보드는 헤더 실크(`D5`)로 나오지만 **맨칩 설계는 패드 이름이 곧 핀 이름**이다.
#: KiCad 의 ESP32 심볼은 `IO24` 처럼 낸다. IPC-D-356 핀 이름은 4자에서 잘리는데
#: `IO24` 는 정확히 4자라 살아남는다.
#:
#: 이게 없으면 R01·R02·R03 이 **영원히 못 뜬다** — 우리가 아는 모듈(XIAO)이
#: 스트래핑·플래시 핀을 하나도 안 뽑아놨기 때문이다. 규칙 로직이 아니라
#: 핀 해석 범위가 막힌 곳이었다.
BARE_PAD_PATTERN = re.compile(r"^(?:IO|GPIO)(\d{1,2})$", re.I)

#: 맨칩으로 인정할 최소 IO 패드 수. 커넥터의 `IO1` 하나를 칩으로 오인하지 않는다.
MIN_BARE_IO_PADS = 4

COLUMN_TOL_INCH = 0.02

#: 헤더 열로 인정할 최소 패드 수. 두세 개짜리 우연한 정렬을 걸러낸다.
MIN_COLUMN_PADS = 4

#: 실크 이름으로 모듈을 인정할 최소 일치 수.
#:
#: 회로도 심볼이 헤더 이름을 다르게 쓸 수 있다 (`GPIO2` · `IO2` · `2`).
#: 한두 개 우연히 맞은 것으로 모듈을 단정하면 **GPIO 번호를 지어내는 것**이고,
#: 그 위에 올라가는 R07·R08 이 통째로 거짓말이 된다.
MIN_SILK_MATCHES = 4


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

    # 회로도 넷리스트는 부품번호를 실어 온다. 좌표가 없는 대신 그게 있다.
    mpns: "dict[str, str]" = {
        ref: part.mpn
        for ref, part in getattr(netlist, "components", {}).items()
        if getattr(part, "mpn", None)
    }

    identities: "list[PadIdentity]" = []
    matched: "dict[str, str]" = {}

    for ref, pads in pads_by_ref.items():
        hit = False
        for module in MODULES.values():
            found = _match_part(ref, pads, module)
            if found:
                identities.extend(found)
                matched[ref] = module.id
                hit = True
                break

        # 기하로 못 풀었으면 **부품번호 + 핀 이름**으로 푼다.
        if not hit and ref in mpns:
            module = _module_from_mpn(mpns[ref])
            if module is not None:
                found = _match_by_silk(ref, pads, module)
                if found:
                    identities.extend(found)
                    matched[ref] = module.id
                    hit = True

        if not hit:
            identities.extend(_bare_chip(ref, pads))

    return PinMap(identities, matched)


def _module_from_mpn(mpn: str) -> "ModulePinout | None":
    """부품번호에서 모듈을 알아본다. `XIAO ESP32C6` · `XIAO-ESP32C6` 둘 다 같다.

    긴 id 부터 본다 — 짧은 id 가 긴 것 안에 들어 있을 수 있다 (`_chip_from_mpn` 과 같은 이유).
    """
    key = "".join(ch for ch in mpn.lower() if ch.isalnum())
    for module_id in sorted(MODULES, key=len, reverse=True):
        if "".join(ch for ch in module_id.lower() if ch.isalnum()) in key:
            return MODULES[module_id]
    return None


def _match_by_silk(ref: str, pads: "list[Pad]", module: ModulePinout) -> "list[PadIdentity]":
    """**부품번호가 모듈을 말해 주면, 핀 이름으로 실크를 푼다.**

    기하가 필요 없는 경로다. 회로도 넷리스트에는 좌표가 없어서 `_match_part` 의
    열 서명이 못 서는데, 대신 핀 이름이 안 잘린 채로 오고 부품번호도 함께 온다.

    **이게 없으면 회로도로 올린 보드에서 R07·R08 이 통째로 조용하다.** 실제로
    우리 REV2 보드가 그 상태였고, 센서 핀을 옮겨도 드리프트가 "변화 없음" 이었다.

    한두 개 맞은 것으로 단정하지 않는다 (`MIN_SILK_MATCHES`) — 심볼이 헤더를
    다르게 부르면 GPIO 번호를 지어내는 셈이고, 그 위의 규칙이 전부 거짓이 된다.
    """
    silk_to_gpio = module.silk_to_gpio
    # **확인은 전원 핀 이름까지 센다.** 회로도는 쓰는 핀만 그리는 일이 흔해서
    # GPIO 실크가 두어 개뿐일 수 있는데, `5V`·`GND`·`3V3` 이 같이 맞으면 그 부품이
    # 이 모듈이라는 증거는 그만큼 더 세다. **신원을 붙이는 것은 GPIO 가 있는 핀뿐이다.**
    all_silks = {p.silk for col in module.columns for p in col}

    corroborating = 0
    found: "list[PadIdentity]" = []
    for pad in pads:
        silk = (pad.name or "").strip()
        if not silk or silk not in all_silks:
            continue
        corroborating += 1
        gpio = silk_to_gpio.get(silk)
        if gpio is None:
            continue  # 전원·접지 핀은 증거로만 쓰고 신원은 안 붙인다
        found.append(
            PadIdentity(
                ref=ref, pin=pad.pin, x=pad.x, y=pad.y,
                silk=silk, gpio=gpio, module=module.id,
            )
        )
    return found if corroborating >= MIN_SILK_MATCHES else []


def _bare_chip(ref: str, pads: "list[Pad]") -> "list[PadIdentity]":
    """패드 이름이 곧 핀 이름인 맨칩 설계에서 GPIO 를 읽는다.

    모듈로 못 알아본 부품에만 시도한다. 어느 칩인지는 **여기서 정하지 않는다** —
    패드 이름은 GPIO 번호만 말해 주고, 그 번호가 스트래핑인지 플래시인지는
    칩마다 다르다. 칩은 BOM 의 부품번호로 규칙이 정한다.

    **이름이 있으면 이름을 본다.** 회로도 넷리스트(kicadxml)로 들어온 보드는
    핀 이름이 잘리지 않은 채 온다 (`GPIO3`). IPC-D-356 은 그 칸이 4자라
    `IO24` 처럼 딱 맞는 것만 살아남았는데, 그게 R07·R08 이 KiCad 보드에서
    통째로 침묵하던 이유였다 (`_docs/규모_실험.md` B).
    """
    found: "list[PadIdentity]" = []
    for pad in pads:
        label = (pad.name or pad.pin).strip()
        m = BARE_PAD_PATTERN.match(label)
        if m:
            found.append(
                PadIdentity(
                    ref=ref, pin=pad.pin, x=pad.x, y=pad.y,
                    silk=label, gpio=int(m.group(1)), module="",
                )
            )
    # 커넥터에 `IO1` 하나 붙은 것을 칩으로 오인하면 그 뒤가 전부 오탐이다.
    return found if len(found) >= MIN_BARE_IO_PADS else []
