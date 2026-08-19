"""IPC-D-356 넷리스트 파서.

_incoming/parse_d356.py 를 그대로 이식한 것이다. 오프셋과 판정 의미를 바꾸지 않았다.

고정폭 레코드 (0-indexed, 실측 검증):
  [0:3]    레코드 타입   317=through-hole/via, 327=SMT
                        (도구마다 다른 것도 온다 — KiCad 367=비도금홀, Eagle 347=홀)
  [3:17]   네트명 (14자)
  [20:26]  reference designator (6자)
  [26]     '-' 구분자
  [27:31]  핀 이름 (4자)   ← 4글자에서 잘린다. 정확한 GPIO 번호를 알 수 없는 원인.
  [32:37]  드릴 'D'+4
  [37]     도금 P/U
  [38:41]  access 'A00'~'A03'
  [41:49]  X 'X'+부호+6자리 (0.0001 inch)
  [49:57]  Y 'Y'+부호+6자리
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

#: 전기적 연결을 담은 레코드. 판정에 쓰는 것은 이것뿐이다.
RECORD_TYPES = {"317": "THRU/VIA", "327": "SMT"}

#: 전기적 연결이 아니라서 빼는 레코드.
#: **빼는 건 맞지만 조용히 빼지 않는다** (CLAUDE.md 2-4).
#: 도구마다 코드가 다르다 — KiCad 는 비도금 홀을 367, Eagle ULP 은 홀을 347 로 낸다.
NON_ELECTRICAL_TYPES = {
    "347": "홀 (Eagle)",
    "367": "비도금 홀 (KiCad)",
}

#: 좌표 단위는 `P UNITS CUST n` 줄이 선언한다.
#: CUST 0 = 인치(0.0001), CUST 1 = 미터법(0.001mm).
#: 지금까지 실측한 도구는 전부 CUST 0 이다 (Flux · KiCad · Eagle ULP).
#: 미터법 파일을 인치로 읽으면 좌표가 25.4배 틀려 패드 그룹이 잘못 나뉜다.
#: 그러면 핀을 잘못 짚고, 그 위에 세운 판정이 전부 틀린다. 그래서 조용히 넘기지 않는다.
UNITS_IMPERIAL = "0"
COORD_SCALE = 10000
_UNITS = re.compile(r"^P\s+UNITS\s+CUST\s+(\d)", re.I)

#: 연결이 없는 패드가 모이는 자리표시 네트명. 네트 수에 세지 않는다.
NO_CONNECT = "N/C"

#: 네트명 칸의 폭. **이 길이에 꽉 찬 이름은 잘렸을 수 있다** (A++2).
#: 핀 이름이 4자에서 잘리는 것과 같은 문제인데, 이쪽은 더 조용하게 아프다 —
#: 이름 끝의 전압 토큰이 날아가면 R11 이 아무 말도 안 하고,
#: 서로 다른 두 네트가 같은 14자로 뭉치면 **없는 연결이 생긴다.**
#:
#: 실측 보드의 `_IN_ACTIVE_LOW` · `D_POS_SWITCHED` 가 정확히 14자다.
#: 앞이 잘린 흔적(`_` 로 시작)이 남아 있어서, 이 도구는 **뒤가 아니라 앞을** 잘랐다.
NET_NAME_WIDTH = 14

_XY = re.compile(r"X([+-]\d{6})Y([+-]\d{6})")

_NET = slice(3, 17)
_REFDES = slice(20, 26)
_PIN = slice(27, 31)


class NetlistParseError(ValueError):
    """넷리스트로 읽을 수 없는 파일."""


@dataclass(frozen=True)
class Pad:
    """레코드 한 줄 = 패드 하나."""

    ref: str
    pin: str
    record: str
    x: float | None = None
    y: float | None = None
    #: 핀의 **이름**(기능). IPC-D-356 에는 없다 — 4자 칸에 잘린 `pin` 이 전부다.
    #: 회로도 넷리스트(kicadxml)로 들어온 보드에만 채워진다 (`GPIO3` · `U0TXD`).
    #: 없으면 None 이다. **없는 것을 지어내지 않는다.**
    name: str | None = None

    @property
    def is_via(self) -> bool:
        return self.ref == "VIA"


class Netlist:
    """파싱 결과. 네트는 파일에 나온 순서를 그대로 유지한다."""

    def __init__(
        self,
        nets: "OrderedDict[str, list[Pad]]",
        parts: "OrderedDict[str, set[str]]",
        meta: list[str],
        filename: str = "",
        non_electrical: "OrderedDict[str, int] | None" = None,
        unknown_records: "OrderedDict[str, int] | None" = None,
    ) -> None:
        self.nets = nets
        self.parts = parts
        self.meta = meta
        self.filename = filename
        #: 전기적 연결이 아니라 뺀 레코드 (타입 → 개수). 정상이지만 기록해 둔다.
        self.non_electrical = non_electrical or OrderedDict()
        #: **우리가 모르는 레코드** (타입 → 개수). 연결을 놓쳤을 수 있으므로 반드시 알린다.
        self.unknown_records = unknown_records or OrderedDict()

    def parse_notes(self) -> list[str]:
        """파일을 읽으며 뺀 것. 화면과 파이프라인이 그대로 보여준다."""
        notes: list[str] = []
        for code, n in self.non_electrical.items():
            notes.append(f"{NON_ELECTRICAL_TYPES.get(code, code)} {n}줄 제외")
        for code, n in self.unknown_records.items():
            notes.append(f"⚠ 모르는 레코드 {code} {n}줄 — 연결을 놓쳤을 수 있습니다")
        clipped = self.width_limited_nets()
        if clipped:
            notes.append(
                f"⚠ 네트명 {len(clipped)}개가 {NET_NAME_WIDTH}자에 꽉 참 "
                f"({' · '.join(clipped[:4])}) — 원래 이름이 잘렸을 수 있습니다"
            )
        return notes

    # ------------------------------------------------------- 네트명 절단 (A++2)

    @staticmethod
    def is_name_at_width_limit(net: str | None) -> bool:
        """이 이름이 칸을 꽉 채웠는가.

        **잘렸다고 단정하지 않는다.** 정확히 14자인 이름을 지은 것일 수도 있다.
        말할 수 있는 건 "이 파일은 더 긴 이름을 담을 수 없었다" 까지다 (헌법 2-2).
        """
        return len(net or "") >= NET_NAME_WIDTH

    def width_limited_nets(self) -> list[str]:
        """칸을 꽉 채운 네트 이름들. 등장 순서를 지킨다."""
        return [n for n in self.ordered_net_names() if self.is_name_at_width_limit(n)]

    # ------------------------------------------------------------------ 조회

    def signal_and_power_nets(self) -> "OrderedDict[str, list[Pad]]":
        """이름이 있고 N/C 가 아닌 네트. 화면과 요약이 세는 기준이다."""
        return OrderedDict((n, p) for n, p in self.nets.items() if n and n != NO_CONNECT)

    def connection_pads(self, net: str) -> list[Pad]:
        """이 네트에 붙은 패드. VIA 는 빼고 같은 (ref, pin) 은 첫 등장만 남긴다."""
        seen: set[tuple[str, str]] = set()
        out: list[Pad] = []
        for pad in self.nets.get(net, []):
            if pad.is_via:
                continue
            key = (pad.ref, pad.pin)
            if key not in seen:
                seen.add(key)
                out.append(pad)
        return out

    def connections(self, net: str) -> list[tuple[str, str]]:
        """(ref, pin) 목록."""
        return [(p.ref, p.pin) for p in self.connection_pads(net)]

    def pads_of(self, ref: str) -> list[Pad]:
        """부품 하나의 모든 패드. 이름이 같아도 좌표가 다르면 다른 패드다."""
        return [
            pad
            for pads in self.nets.values()
            for pad in pads
            if pad.ref == ref and not pad.is_via
        ]

    def via_count(self, net: str) -> int:
        return sum(1 for pad in self.nets.get(net, []) if pad.is_via)

    def net_of(self, ref: str, pin: str) -> str | None:
        """부품 핀 하나가 어느 네트에 붙어 있는지.

        같은 이름의 패드가 여럿이면 첫 번째만 나온다 — 그게 IPC-D-356 의 한계다.
        패드를 정확히 지목하려면 `net_at()` 을 쓴다.
        """
        for net, pads in self.nets.items():
            for pad in pads:
                if pad.ref == ref and pad.pin == pin:
                    return net
        return None

    def net_at(self, ref: str, pin: str, x: float | None, y: float | None) -> str | None:
        """좌표까지 지정해 패드 하나를 정확히 짚는다. D3 와 D4 와 D5 를 구분하는 유일한 방법."""
        for net, pads in self.nets.items():
            for pad in pads:
                if pad.ref == ref and pad.pin == pin and pad.x == x and pad.y == y:
                    return net
        return None

    @staticmethod
    def is_unconnected(net: str | None) -> bool:
        """이름만 보고 판단한다. 빈 이름과 N/C 를 같게 본다.

        **이름만으로는 부족하다.** 토폴로지까지 보려면 `is_dangling()` 을 쓴다.
        """
        return not net or net == NO_CONNECT

    def is_dangling(self, net: str | None) -> bool:
        """이 패드에 **전기적으로** 상대가 없는가.

        이름만 보면 도구가 바뀌는 순간 틀린다. kicad-cli 는 미연결 패드를
        `unconnected-(U3-SPICLK-Pad22)` 라는 유사 네트로 내보내는데,
        IPC-D-356 네트명 필드가 14자라 **앞의 `unconnected-` 가 잘려 나간다.**

            원본   unconnected-(U3-SPICLK-Pad22)
            d356   -SPICLK-PAD22)        ← 진짜 네트처럼 보인다

        실측(ESP32-C3 오픈소스 보드): `.kicad_pcb` 의 unconnected 32개 중
        `N/C` 로 온 것은 2개뿐이고 16개가 이런 유사 네트로 왔다.
        그대로 두면 R07 은 침묵하고(미탐) R08 은 오탐을 낸다.

        **상대가 없으면 연결이 아니다.** 패드 수로 본다 — 도구와 이름에 무관하다.
        """
        if Netlist.is_unconnected(net):
            return True
        return len(self.connection_pads(net or "")) <= 1

    @property
    def net_count(self) -> int:
        return len(self.signal_and_power_nets())

    @property
    def part_count(self) -> int:
        return len(self.parts)

    # ------------------------------------------------------------------ 직렬화

    def ordered_net_names(self) -> list[str]:
        """부록에 싣는 순서: 연결이 많은 네트부터, 같으면 이름순.

        전원·접지가 위로 올라와서 사람이 읽기 좋다. 프로토타입 출력 순서와 같다.
        """
        return sorted(
            self.signal_and_power_nets(),
            key=lambda n: (-len(self.connections(n)), n),
        )

    def to_dict(self, pinmap=None, bom=None) -> dict:
        """API_CONTRACT.md 의 `netlist` 블록.

        `pinmap` 이 있으면 패드마다 `silk` · `gpio` 를 **선택 필드로 덧붙인다.**
        기존 필드는 하나도 바뀌지 않는다 — 없어도 화면은 지금처럼 동작한다.
        """

        def decorate(pad: Pad) -> dict:
            out = {"ref": pad.ref, "pin": pad.pin}
            identity = pinmap.of(pad) if pinmap else None
            if identity is not None:
                out["silk"] = identity.silk
                if identity.gpio is not None:
                    out["gpio"] = identity.gpio
            return out

        def part(ref: str) -> dict:
            mpn = bom.mpn_of(ref) if bom else None
            out = {"ref": ref, "pins": sorted(self.parts[ref]), "mpn": mpn}
            if not pinmap:
                return out
            pads = [
                {"pin": p.pin, "silk": i.silk, "gpio": i.gpio}
                for p in self.pads_of(ref)
                for i in [pinmap.of(p)]
                if i is not None
            ]
            if pads:
                # 이름이 4자로 뭉쳐 잃어버린 구분을 여기서 되돌려 준다.
                # 25개 패드가 18개 이름으로 보이던 문제.
                out["pads"] = sorted(
                    pads, key=lambda d: (d["gpio"] is None, d["gpio"] or 0, d["silk"])
                )
            return out

        return {
            "nets": [
                {
                    "name": name,
                    "vias": self.via_count(name),
                    "connections": [decorate(p) for p in self.connection_pads(name)],
                }
                for name in self.ordered_net_names()
            ],
            "parts": [part(ref) for ref in sorted(self.parts)],
        }


def parse_text(text: str, filename: str = "") -> Netlist:
    nets: "OrderedDict[str, list[Pad]]" = OrderedDict()
    parts: "OrderedDict[str, set[str]]" = OrderedDict()
    meta: list[str] = []
    non_electrical: "OrderedDict[str, int]" = OrderedDict()
    unknown: "OrderedDict[str, int]" = OrderedDict()

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line:
            continue
        if line.startswith("P "):
            meta.append(line.strip())
            um = _UNITS.match(line)
            if um and um.group(1) != UNITS_IMPERIAL:
                raise NetlistParseError(
                    f"좌표 단위가 인치가 아닙니다 (P UNITS CUST {um.group(1)}). "
                    "지금 파서는 0.0001 inch 단위(CUST 0)만 읽습니다. "
                    "이대로 읽으면 좌표가 어긋나 핀 그룹이 잘못 나뉘고 판정이 틀립니다."
                )
            continue
        if line.startswith("999"):
            break

        record = line[0:3]
        if record not in RECORD_TYPES:
            # 버리더라도 무엇을 버렸는지 남긴다. 모르는 타입은 연결을 놓친 것일 수 있다.
            if record in NON_ELECTRICAL_TYPES:
                non_electrical[record] = non_electrical.get(record, 0) + 1
            elif record[:1].isdigit():
                unknown[record] = unknown.get(record, 0) + 1
            continue

        net = line[_NET].strip()
        refdes = line[_REFDES].strip()
        pin = line[_PIN].strip() if len(line) > _PIN.start else ""

        m = _XY.search(line)
        x, y = (
            (int(m.group(1)) / COORD_SCALE, int(m.group(2)) / COORD_SCALE) if m else (None, None)
        )

        bucket = nets.setdefault(net, [])
        if refdes.upper() == "VIA" or not refdes:
            bucket.append(Pad(ref="VIA", pin="", record=record, x=x, y=y))
            continue

        bucket.append(Pad(ref=refdes, pin=pin, record=record, x=x, y=y))
        if pin:
            parts.setdefault(refdes, set()).add(pin)

    if not parts:
        raise NetlistParseError(
            "IPC-D-356 레코드를 한 줄도 찾지 못했습니다. "
            "317/327 로 시작하는 고정폭 레코드가 있는 파일인지 확인해 주세요."
        )

    return Netlist(
        nets=nets,
        parts=parts,
        meta=meta,
        filename=filename,
        non_electrical=non_electrical,
        unknown_records=unknown,
    )


def parse(path: "str | Path") -> Netlist:
    p = Path(path)
    return parse_text(p.read_text(encoding="utf-8", errors="replace"), filename=p.name)
