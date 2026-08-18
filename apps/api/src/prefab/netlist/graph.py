"""부품·네트 그래프와 전원 도메인 추론.

_incoming/check.py 의 build / cluster_pads / supply_domain 을 의미 그대로 이식했다.
개선하지 않았다. 임계값은 전부 이름 있는 상수로 올렸다 (CLAUDE.md 10절).
"""

from __future__ import annotations

import re
from collections import OrderedDict, defaultdict
from dataclasses import dataclass

from .d356 import NO_CONNECT, Netlist, Pad
from .pinmap import PinMap, resolve as resolve_pinmap

# --------------------------------------------------------------------- 상수

#: 접지로 취급할 네트명 접두사
GND_PATTERN = re.compile(r"^(GND|VSS|AGND|DGND)", re.I)

#: 전원 입력 핀으로 취급할 핀 이름 접두사
SUPPLY_PIN_PATTERN = re.compile(r"^(VCC|VDD|VIN|VBUS|V\+|5V|3V3|3\.3V|VDDIO)", re.I)

#: 부품이 자기 IO 레일을 직접 노출하는 핀 이름 (VCC 보다 우선한다)
IO_RAIL_PIN_PATTERN = re.compile(r"^(3V3|3\.3V|VDDIO)", re.I)

#: 이름 안에 박힌 전압 토큰. 5V, 3V3, 1V8, 12V
VOLTAGE_TOKEN = re.compile(r"(?<![A-Z0-9])(\d{1,2})V(\d)?(?![A-Z0-9])", re.I)

#: 전원 도메인을 추론하지 않는 수동 부품
PASSIVE_REF_PATTERN = re.compile(r"^(R|C|L|D|FB)\d")

#: 직렬 보호 소자 후보로 볼 부품 (저항·다이오드)
SERIES_CANDIDATE_PATTERN = re.compile(r"^(R|D)\d")

#: 패드 X좌표 클러스터링 허용 오차 (inch).
#: 프로토타입의 tol=0.05 × 20 을 그대로 옮긴 값이다.
PAD_CLUSTER_TOL_INCH = 1.0

#: 이 값보다 큰 전압 차이만 도메인이 다르다고 본다 (V).
DOMAIN_EPSILON_V = 0.15

#: 전압 이름을 가진 네트에 이 수를 넘는 부품이 붙어 있으면 신호가 아니라 전원 레일로 본다.
POWER_RAIL_FANOUT_MIN = 4

CONFIDENCE_HIGH = "high"
CONFIDENCE_INFERRED = "inferred"
CONFIDENCE_NONE = "none"

#: 네트에 붙은 수동 소자의 정체. 반대쪽 터미널이 어디로 가느냐로 갈린다.
ROLE_PULLUP = "풀업"
ROLE_PULLDOWN = "풀다운"
ROLE_BRANCH = "분기"
ROLE_UNKNOWN = "미상"

#: 출력이라고 이름이 말해 주는 핀. 이것 말고는 방향을 단정하지 않는다.
OUTPUT_PIN_PATTERN = re.compile(r"^(OUT|DOUT|TXD|TX|MISO|MOSI)", re.I)


def volts(name: str | None) -> float | None:
    """이름이 주장하는 전압. 없으면 None."""
    m = VOLTAGE_TOKEN.search(name or "")
    if not m:
        return None
    whole, frac = m.group(1), m.group(2)
    return float(f"{whole}.{frac}") if frac else float(whole)


def format_volts(value: float | None) -> str:
    """사람에게 보여줄 전압 문자열. 5.0 → '5', 3.3 → '3.3'."""
    if value is None:
        return "?"
    return f"{value:g}"


@dataclass(frozen=True)
class PassiveRole:
    """네트에 붙은 저항·다이오드가 무엇을 하고 있는가."""

    role: str
    other_net: str | None
    phrase: str

    @property
    def protects(self) -> bool:
        """직렬 보호가 되는가. 풀업도 풀다운도 분기도 보호가 아니다."""
        return False


@dataclass(frozen=True)
class Domain:
    """부품 하나의 전원 도메인 추론 결과."""

    volts: float | None
    basis: str
    confidence: str

    @property
    def known(self) -> bool:
        return self.volts is not None


PinKey = tuple[str, str, tuple[float | None, float | None]]


class Graph:
    """넷리스트 위에 얹은 부품·네트 뷰. 규칙은 이 객체만 본다."""

    def __init__(self, netlist: Netlist) -> None:
        self.netlist = netlist
        #: 패드마다 확정된 실크·GPIO. 모듈을 못 알아보면 비어 있다.
        self.pinmap: PinMap = resolve_pinmap(netlist)
        self.part_pins: "dict[str, dict[PinKey, str]]" = self._build(netlist)
        self._domains: "OrderedDict[str, Domain]" = OrderedDict()
        for ref in sorted(self.part_pins):
            if PASSIVE_REF_PATTERN.match(ref):
                continue
            self._domains[ref] = self._supply_domain(ref)

    # ------------------------------------------------------------------ 구축

    @staticmethod
    def _build(netlist: Netlist) -> "dict[str, dict[PinKey, str]]":
        part_pins: "dict[str, dict[PinKey, str]]" = defaultdict(dict)
        for net, pads in netlist.nets.items():
            for pad in pads:
                if pad.is_via:
                    continue
                key: PinKey = (pad.ref, pad.pin, (pad.x, pad.y))
                part_pins[pad.ref][key] = net
        return dict(part_pins)

    # ------------------------------------------------------------------ 조회

    def domain(self, ref: str) -> Domain:
        return self._domains.get(ref, Domain(None, "unknown", CONFIDENCE_NONE))

    def domains(self) -> "OrderedDict[str, Domain]":
        return self._domains

    def pins_of(self, ref: str) -> "OrderedDict[str, set[str]]":
        """핀 이름 → 그 핀이 붙은 네트들. 같은 이름의 패드가 여러 개일 수 있다."""
        named: "OrderedDict[str, set[str]]" = OrderedDict()
        for (_r, pin, _coord), net in self.part_pins.get(ref, {}).items():
            named.setdefault(pin, set()).add(net)
        return named

    def pin_on_net(self, ref: str, net: str) -> str | None:
        """부품 ref 가 네트 net 에 붙어 있는 핀 이름 (넷리스트 원본, 4자로 잘린 것)."""
        for (_r, pin, _coord), n in self.part_pins.get(ref, {}).items():
            if n == net:
                return pin
        return None

    def display_pin(self, ref: str, net: str) -> str | None:
        """근거에 찍을 핀 이름. 핀맵이 풀렸으면 **실크 라벨**을 쓴다.

        `U1.SDIO` 는 D3·D4·D5 중 무엇인지 말해 주지 않는다. `U1.D5` 라고 써야
        사람이 보드에서 그 핀을 찾을 수 있다.
        """
        for (_r, pin, coord), n in self.part_pins.get(ref, {}).items():
            if n != net:
                continue
            for identity in self.pinmap.all():
                if identity.ref == ref and identity.pin == pin and (identity.x, identity.y) == coord:
                    return identity.silk
            return pin
        return None

    def ref_pin(self, ref: str, net: str) -> str:
        """`U1.D5` 형태의 표시용 토큰."""
        return f"{ref}.{self.display_pin(ref, net) or '?'}"

    def drives(self, ref: str, net: str) -> bool:
        """이 부품이 이 네트를 구동한다고 **넷리스트가 말해 주는가.**

        핀 이름이 출력이라고 말할 때만 True 다. 이름 없는 패드(`pad-`)에서는
        방향을 알 수 없으므로 단정하지 않는다 (요청서 A-2).
        """
        pin = self.pin_on_net(ref, net)
        return bool(pin and OUTPUT_PIN_PATTERN.match(pin))

    def supply_pin_of(self, ref: str) -> tuple[str, str] | None:
        """(전원 핀 이름, 그 핀이 물린 레일 네트). 이름 없는 패드뿐이면 None."""
        named = self.pins_of(ref)
        for pattern in (IO_RAIL_PIN_PATTERN, SUPPLY_PIN_PATTERN):
            for pin, nets in named.items():
                if pattern.match(pin):
                    for n in nets:
                        if volts(n):
                            return pin, n
        return None

    def clusters(self, ref: str) -> "dict[float, list[tuple[str, str]]]":
        """이름이 전부 같은 패드를 X좌표로 물리 그룹으로 나눈다.

        기하가 이름이 잃어버린 것을 복원한다 (K1 의 6개 패드가 전부 'pad-').
        """
        groups: "dict[float, list[tuple[str, str]]]" = defaultdict(list)
        for (_r, pin, coord), net in self.part_pins.get(ref, {}).items():
            x = coord[0] if coord[0] is not None else 0.0
            placed = False
            for gx in list(groups):
                if abs(gx - x) < PAD_CLUSTER_TOL_INCH:
                    groups[gx].append((pin, net))
                    placed = True
                    break
            if not placed:
                groups[x].append((pin, net))
        return dict(groups)

    # ------------------------------------------------------------------ 추론

    def _supply_domain(self, ref: str) -> Domain:
        named = self.pins_of(ref)

        # 1. 자기 IO 레일을 직접 노출하는 핀이 있으면 그것이 IO 전압이다.
        for pin, nets in named.items():
            if IO_RAIL_PIN_PATTERN.match(pin):
                for n in nets:
                    v = volts(n)
                    if v:
                        return Domain(v, f"{ref}.{pin} → {n}", CONFIDENCE_HIGH)

        # 2. 없으면 VCC/VDD/VIN 을 먹이는 레일.
        for pin, nets in named.items():
            if SUPPLY_PIN_PATTERN.match(pin):
                for n in nets:
                    v = volts(n)
                    if v:
                        return Domain(v, f"{ref}.{pin} → {n}", CONFIDENCE_HIGH)

        # 3. 이름 없는 패드뿐이면 (K1 의 'pad-'),
        #    전원+접지가 같이 들어 있는 X클러스터에서 레일을 읽는다.
        for gx, members in self.clusters(ref).items():
            rails = [volts(n) for _p, n in members if volts(n) and not GND_PATTERN.match(n)]
            has_gnd = any(GND_PATTERN.match(n) for _p, n in members)
            if rails and has_gnd:
                return Domain(
                    max(rails),
                    f"{ref} 패드 클러스터 @X{gx:+.4f} (레일+GND 동거)",
                    CONFIDENCE_INFERRED,
                )

        return Domain(None, "unknown", CONFIDENCE_NONE)

    # ------------------------------------------------------------------ 네트 분류

    def signal_nets(self) -> "OrderedDict[str, list[Pad]]":
        """판정 대상 네트. 접지와 전원 레일은 뺀다."""
        out: "OrderedDict[str, list[Pad]]" = OrderedDict()
        for net, pads in self.netlist.nets.items():
            if not net or net == NO_CONNECT:
                continue
            if GND_PATTERN.match(net):
                continue
            refs = {p.ref for p in pads if not p.is_via}
            if volts(net) and len(refs) > POWER_RAIL_FANOUT_MIN:
                continue  # 전압 이름 + 팬아웃 많음 = 전원 레일
            out[net] = pads
        return out

    def active_refs(self, net: str) -> list[str]:
        """이 네트에 붙어 있고 전원 도메인을 아는 능동 부품."""
        refs = sorted({p.ref for p in self.netlist.nets.get(net, []) if not p.is_via})
        return [r for r in refs if self.domain(r).known]

    def refs_on(self, net: str) -> list[str]:
        return sorted({p.ref for p in self.netlist.nets.get(net, []) if not p.is_via})

    def series_candidates(self, net: str) -> list[str]:
        return [r for r in self.refs_on(net) if SERIES_CANDIDATE_PATTERN.match(r)]

    # ------------------------------------------------------------------ 수동 소자

    def other_nets(self, ref: str, net: str) -> list[str]:
        """부품 ref 의 나머지 터미널이 물린 네트들."""
        return sorted({n for n in self.part_pins.get(ref, {}).values() if n != net})

    def passive_role(self, ref: str, net: str) -> "PassiveRole":
        """이 네트에 붙은 수동 소자가 무엇인지 **반대쪽 터미널을 보고** 판정한다.

        반대쪽을 안 보고 전부 "풀업"이라고 쓰던 버그가 있었다 (요청서 2-6).
        판정(FAIL)은 어느 쪽이든 같지만, 근거 문구가 틀리면 판정이 맞아도 신뢰를 잃는다.
        """
        others = self.other_nets(ref, net)
        if not others:
            return PassiveRole(ROLE_UNKNOWN, None, "반대쪽 터미널을 찾지 못했습니다")

        for other in others:
            if GND_PATTERN.match(other):
                return PassiveRole(ROLE_PULLDOWN, other, f"{other} 로 끌어내리는 풀다운")

        for other in others:
            v = volts(other)
            if v is not None:
                return PassiveRole(ROLE_PULLUP, other, f"{other} 로 끌어올리는 풀업")

        other = others[0]
        return PassiveRole(ROLE_BRANCH, other, f"{other} 로 이어지는 분기")
