"""IPC-D-356 넷리스트 파서.

_incoming/parse_d356.py 를 그대로 이식한 것이다. 오프셋과 판정 의미를 바꾸지 않았다.

고정폭 레코드 (0-indexed, 실측 검증):
  [0:3]    레코드 타입   317=through-hole/via, 327=SMT
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

#: 우리가 읽는 레코드 타입만 남긴다. 나머지 줄은 조용히 버린다.
RECORD_TYPES = {"317": "THRU/VIA", "327": "SMT"}

#: 좌표는 0.0001 inch 단위로 적혀 있다.
COORD_SCALE = 10000

#: 연결이 없는 패드가 모이는 자리표시 네트명. 네트 수에 세지 않는다.
NO_CONNECT = "N/C"

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
    ) -> None:
        self.nets = nets
        self.parts = parts
        self.meta = meta
        self.filename = filename

    # ------------------------------------------------------------------ 조회

    def signal_and_power_nets(self) -> "OrderedDict[str, list[Pad]]":
        """이름이 있고 N/C 가 아닌 네트. 화면과 요약이 세는 기준이다."""
        return OrderedDict((n, p) for n, p in self.nets.items() if n and n != NO_CONNECT)

    def connections(self, net: str) -> list[tuple[str, str]]:
        """(ref, pin) 목록. VIA 는 빼고 중복은 첫 등장만 남긴다."""
        seen: set[tuple[str, str]] = set()
        out: list[tuple[str, str]] = []
        for pad in self.nets.get(net, []):
            if pad.is_via:
                continue
            key = (pad.ref, pad.pin)
            if key not in seen:
                seen.add(key)
                out.append(key)
        return out

    def via_count(self, net: str) -> int:
        return sum(1 for pad in self.nets.get(net, []) if pad.is_via)

    def net_of(self, ref: str, pin: str) -> str | None:
        """부품 핀 하나가 어느 네트에 붙어 있는지."""
        for net, pads in self.nets.items():
            for pad in pads:
                if pad.ref == ref and pad.pin == pin:
                    return net
        return None

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

    def to_dict(self) -> dict:
        """API_CONTRACT.md 의 `netlist` 블록."""
        return {
            "nets": [
                {
                    "name": name,
                    "vias": self.via_count(name),
                    "connections": [{"ref": r, "pin": p} for r, p in self.connections(name)],
                }
                for name in self.ordered_net_names()
            ],
            "parts": [
                {"ref": ref, "pins": sorted(self.parts[ref]), "mpn": None}
                for ref in sorted(self.parts)
            ],
        }


def parse_text(text: str, filename: str = "") -> Netlist:
    nets: "OrderedDict[str, list[Pad]]" = OrderedDict()
    parts: "OrderedDict[str, set[str]]" = OrderedDict()
    meta: list[str] = []

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line:
            continue
        if line.startswith("P "):
            meta.append(line.strip())
            continue
        if line.startswith("999"):
            break

        record = line[0:3]
        if record not in RECORD_TYPES:
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

    return Netlist(nets=nets, parts=parts, meta=meta, filename=filename)


def parse(path: "str | Path") -> Netlist:
    p = Path(path)
    return parse_text(p.read_text(encoding="utf-8", errors="replace"), filename=p.name)
