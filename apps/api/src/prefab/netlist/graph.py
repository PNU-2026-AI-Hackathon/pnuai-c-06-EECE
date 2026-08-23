"""부품·네트 그래프와 전원 도메인 추론.

_incoming/check.py 의 build / cluster_pads / supply_domain 을 의미 그대로 이식했다.
개선하지 않았다. 임계값은 전부 이름 있는 상수로 올렸다 (CLAUDE.md 10절).
"""

from __future__ import annotations

import re
from collections import OrderedDict, defaultdict
from dataclasses import dataclass

from ..chips import CHIPS, MODULES
from .d356 import NO_CONNECT, Netlist, Pad
from .pinmap import PinMap, resolve as resolve_pinmap

# --------------------------------------------------------------------- 상수

#: 접지로 취급할 네트명 접두사
GND_PATTERN = re.compile(r"^(GND|VSS|AGND|DGND)", re.I)


def local_name(net: str) -> str:
    """계층 시트 경로를 벗긴 네트 이름.

    KiCad 는 계층 시트를 쓰면 네트 이름 앞에 경로를 붙인다 — `/GND` · `/Sensor/SDA`.
    이름 패턴은 `^` 로 시작하므로 **접지가 접지로 안 보인다.** 실제로
    오픈소스 보드에서 `/GND` 가 신호 네트로 분류되고 있었다.

    Flux 로 만든 우리 픽스처는 경로가 없어서 이 문제를 한 번도 못 만났다.
    """
    return net.rsplit("/", 1)[-1] if net else net

#: 전원 입력 핀으로 취급할 핀 이름 접두사
SUPPLY_PIN_PATTERN = re.compile(r"^(VCC|VDD|VIN|VBUS|V\+|5V|3V3|3\.3V|VDDIO)", re.I)

#: 부품이 자기 IO 레일을 직접 노출하는 핀 이름 (VCC 보다 우선한다)
IO_RAIL_PIN_PATTERN = re.compile(r"^(3V3|3\.3V|VDDIO)", re.I)

#: 그중 **부품이 스스로 "이게 내 IO 공급이다" 라고 밝힌** 이름.
#: `3V3` 는 여기 안 들어간다 — 개발보드 헤더의 `3V3` 는 IO 선언이 아니라
#: **레귤레이터 출력 핀**이고, 5V 로직 보드에도 그 핀이 있다.
IO_SUPPLY_PIN_PATTERN = re.compile(r"^VDDIO", re.I)

#: **먹는 쪽**이라고 이름이 말하는 전원 핀. `VIN` 은 "내가 받는 전압" 이지
#: "내 로직 전압" 이 아니다 — 5V 를 먹고 안에서 3.3V 를 만드는 부품이 흔하다.
#: 그래서 다른 전원 핀이 있으면 이쪽은 로직 전압 투표에서 뺀다.
SUPPLY_INPUT_PIN_PATTERN = re.compile(r"^(VIN|VBUS|V\+)", re.I)

#: 「레일 소속」 추론(마지막 단계)을 쓰려면 이 부품의 핀 중 전원·접지가 차지하는 최소 비율.
#:
#: 이 추론의 뜻은 "이 부품은 저 레일에서 전원을 받는다" 다. 커넥터처럼 신호를 잔뜩
#: 나르는 부품에서는 그 말이 성립하지 않는다 — 40핀 헤더의 4핀이 전원이라고
#: 나머지 36핀이 그 전압인 것이 아니다.
RAIL_INFERENCE_MIN_POWER_SHARE = 0.5

#: 이름 안에 박힌 전압 토큰. `5V` · `3V3` · `1V8` · `12V` · `+3.3V` · `0.9V`
#:
#: **소수점 표기를 한동안 못 읽었다.** 유럽식(`3V3`)만 보고 있어서 KiCad 가 흔히 쓰는
#: `+3.3V` 를 **3.0V** 로 읽었다. 더 나쁜 것은 `0.9V` 였다 — 앞의 `0.` 을 건너뛰고
#: `9V` 를 잡아 **9.0V** 로 읽었다. 0.9V 코어 레일을 9V 로 보면 R11·R12 가
#: 엉뚱한 과전압 경고를 낸다.
#:
#: 그래서 소수점을 먼저 먹고(`\d{1,2}(?:\.\d{1,2})?`), 앞에 `.` 이 오면 아예 안 잡는다.
#: `0.9V` 의 `9` 자리에서 다시 매칭되는 것을 막는 것이 그 `\.` 이다.
VOLTAGE_TOKEN = re.compile(
    r"(?<![A-Z0-9.])(\d{1,2}(?:\.\d{1,2})?)V(\d)?(?![A-Z0-9])", re.I
)

#: **전압을 모르는 전원 레일.** KiCad 보드는 `+VSW` · `+BATT` 처럼 이름에 숫자가 없다.
#: 전압 토큰만 보면 이런 레일이 신호로 분류돼 오탐의 출처가 된다 (요청서 A+2).
#: 이름만으로는 부족해서 **팬아웃과 함께** 본다 — 이름이 레일 같아도 부품이 둘뿐이면 신호다.
POWER_NAME_PATTERN = re.compile(
    r"^\+|^(VCC|VDD|VDDA|AVDD|DVDD|VBUS|VBAT|VBATT|VSW|VIN|VSYS|VREF|PWR)", re.I
)

#: 전원 도메인을 추론하지 않는 수동 부품
PASSIVE_REF_PATTERN = re.compile(r"^(R|C|L|D|FB)\d")

#: 직렬 보호 소자 후보로 볼 부품 (저항·다이오드)
SERIES_CANDIDATE_PATTERN = re.compile(r"^(R|D)\d")

#: 패드를 다른 물리 그룹으로 가르는 X 간격 (inch).
#:
#: 프로토타입은 "1.0 inch 안이면 같은 그룹"이었다. 그 값은 우리 보드 K1 하나에 맞춰져
#: 있었다 — K1 의 두 그룹이 마침 1.437 inch 떨어져 겨우 갈렸을 뿐이고,
#: 같은 규칙으로 U2(0.1 inch 피치 5패드)는 통째로 한 덩어리가 된다 (요청서 A+6).
#:
#: 그래서 절대 거리가 아니라 **이웃 패드 사이의 간격**으로 가른다. 근거:
#:   - 표준 헤더 피치는 최대 0.1 inch (2.54mm). 2mm · 0.05 inch 는 더 좁다
#:   - 실측: U2 0.1 · R3 0.065 · J1 최대 0.154 → 전부 한 부품이 맞다
#:   - 실측: K1 제어부 ↔ 스위치부 1.437 → 갈라야 한다
#: 0.3 은 최대 피치의 3배이자 K1 간격의 1/4.8 이다. 양쪽에서 여유가 있다.
PAD_CLUSTER_GAP_INCH = 0.3

#: 이 값보다 큰 전압 차이만 도메인이 다르다고 본다 (V).
DOMAIN_EPSILON_V = 0.15

#: 전압 이름을 가진 네트에 이 수를 넘는 부품이 붙어 있으면 신호가 아니라 전원 레일로 본다.
POWER_RAIL_FANOUT_MIN = 4

#: 이 수 이상의 공급 핀이 붙어 있으면 이름과 무관하게 전원 레일이다.
#: 하나로는 부족하다 — 부품 하나가 자기 전원을 받는 것은 그 부품의 사정이다.
SUPPLY_PINS_MIN = 2

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

#: **핀 이름이 스스로 "나는 받는 쪽" 이라고 밝힌** 경우.
#:
#: 좁게 잡는다 — `IN1` · `DIN` 까지만 받고 `INT`(인터럽트) · `INH`(억제) 는 안 받는다.
#: 넓히면 신호 핀을 통째로 입력으로 오인해서 R12 가 침묵한다. 그건 더 나쁜 실패다.
INPUT_PIN_PATTERN = re.compile(r"^(IN|INPUT|DIN)\d*$", re.I)

#: 네트 **이름이 전압을 주장하는 게 아니라 무엇을 제어하는지 말하는** 꼬리표.
#:
#: `24V_ON` 은 24V 네트가 아니라 **24V 를 켜는 신호**다. 3.3V MCU 가 내는 게 정상인데,
#: 이름의 `24V` 를 전압 주장으로 읽고 "구동하는 A3 은 3.3V" 라고 반박하고 있었다.
#: 이름이 제어 대상을 말할 때 그 네트의 전압은 **모르는 것**이다 (헌법 2-2).
CONTROL_SUFFIX_PATTERN = re.compile(r"_(ON|OFF|EN|ENABLE|CTRL|SEL|SW|PWM)\d*$", re.I)


def names_a_control(net: str) -> bool:
    """이 네트 이름이 **자기 전압이 아니라 제어 대상**을 말하고 있는가."""
    return bool(CONTROL_SUFFIX_PATTERN.search(local_name(net or "")))


def volts(name: str | None) -> float | None:
    """이름이 주장하는 전압. 없으면 None."""
    m = VOLTAGE_TOKEN.search(name or "")
    if not m:
        return None
    whole, frac = m.group(1), m.group(2)
    return float(f"{whole}.{frac}") if frac else float(whole)


def voltage_is_clipped(name: str | None, *, width_limited: bool = True) -> bool:
    """이 이름의 전압 토큰을 믿어도 되는가 (A++2).

    네트명 칸은 14자다. 이름이 그 길이에 꽉 찼고 **전압 토큰이 끝에 걸쳐 있으면**
    값이 잘렸을 수 있다 — `..._3V` 는 `_3V3` 의 앞부분일 수 있다.
    3.3V 를 3V 로 읽으면 R11 이 0.3V 차이를 근거로 경고를 낸다. 그게 오탐이다.

    잘렸다고 단정하는 게 아니라 **믿을 수 없다**고 말하는 함수다 (헌법 2-2).
    """
    text = name or ""
    if not width_limited:
        return False  # 길이 제한이 없는 형식이면 잘릴 일이 없다
    if not Netlist.is_name_at_width_limit(text):
        return False
    last = None
    for last in VOLTAGE_TOKEN.finditer(text):
        pass
    return last is not None and last.end() == len(text)


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
        #: 패드 → **사람이 읽는 핀 이름.** 회로도 넷리스트는 `3V3`·`VIN` 처럼 이름을
        #: 실어 주는데, `part_pins` 의 키는 핀 **번호**라 그 이름이 버려졌다.
        #: 그 탓에 전원 도메인 추론이 `VIN`·`3V3` 을 하나도 못 알아보고 패드 클러스터로
        #: 떨어졌고, 5V 를 받아 3.3V 로 도는 개발보드를 **5V 부품으로 판정**했다.
        #: 실보드 하나에서 그 하나 때문에 R12 오탐이 21건 났다.
        self._pin_label: "dict[PinKey, str]" = self._build_labels(netlist)
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

    @staticmethod
    def _build_labels(netlist: Netlist) -> "dict[PinKey, str]":
        """패드마다 **이름이 있으면 이름, 없으면 번호.** pinmap 과 같은 관습이다."""
        labels: "dict[PinKey, str]" = {}
        for pads in netlist.nets.values():
            for pad in pads:
                if pad.is_via:
                    continue
                labels[(pad.ref, pad.pin, (pad.x, pad.y))] = (pad.name or pad.pin or "").strip()
        return labels

    # ------------------------------------------------------------------ 조회

    def _chip_of(self, ref: str):
        """이 부품이 어느 칩인가. 모듈 핀아웃 매칭 결과로만 정한다."""
        module_id = self.pinmap.modules_matched.get(ref)
        module = MODULES.get(module_id) if module_id else None
        return CHIPS.get(module.chip) if module else None

    def _chip_logic_volts(self, ref: str) -> float | None:
        chip = self._chip_of(ref)
        return chip.logic_volts if chip else None

    def _chip_name(self, ref: str) -> str:
        chip = self._chip_of(ref)
        return chip.name if chip else "?"

    def domain(self, ref: str) -> Domain:
        return self._domains.get(ref, Domain(None, "unknown", CONFIDENCE_NONE))

    def domains(self) -> "OrderedDict[str, Domain]":
        return self._domains

    def pins_of(self, ref: str) -> "OrderedDict[str, set[str]]":
        """핀 이름 → 그 핀이 붙은 네트들. 같은 이름의 패드가 여러 개일 수 있다.

        **이름이 있으면 이름을 쓴다.** 번호(`16`)로 돌려주면 `3V3`·`VIN` 같은
        전원 핀 패턴이 하나도 안 걸려서 도메인 추론이 통째로 빗나간다.
        """
        named: "OrderedDict[str, set[str]]" = OrderedDict()
        for key, net in self.part_pins.get(ref, {}).items():
            named.setdefault(self._pin_label.get(key) or key[1], set()).add(net)
        return named

    def pin_on_net(self, ref: str, net: str) -> str | None:
        """부품 ref 가 네트 net 에 붙어 있는 핀 이름 (넷리스트 원본, 4자로 잘린 것)."""
        for key, n in self.part_pins.get(ref, {}).items():
            if n == net:
                return self._pin_label.get(key) or key[1]
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

    def receives(self, ref: str, net: str) -> bool:
        """이 부품이 이 네트에 **받는 쪽 핀으로** 닿아 있는가.

        `drives` 와 짝이고, 마찬가지로 **핀 이름이 그렇게 말할 때만** True 다.
        모르면 False 다 — "입력인지 모른다" 를 "입력이다" 로 쓰면 경고가 조용히 사라진다.

        레벨 시프터에서 실제로 걸렸다. `SN74LV1T34`(5V VCC)의 `IN` 핀이 3.3V MCU 와
        같은 네트에 있다고 R12 가 치명을 냈는데, **그 부품이 바로 문제를 푸는 부품**이다.
        발견 문구가 "레벨 시프터도 없습니다" 라면서 레벨 시프터를 가리키고 있었다.
        받는 쪽 핀은 자기 VCC 를 네트에 올리지 않는다.
        """
        pin = self.pin_on_net(ref, net)
        return bool(pin and INPUT_PIN_PATTERN.match(pin))

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
        X 로 정렬한 뒤 **이웃 간격이 PAD_CLUSTER_GAP_INCH 를 넘는 자리에서** 자른다.
        """
        # **좌표가 없는 형식에서는 아무 말도 하지 않는다.**
        #
        # 없는 좌표를 `0.0` 으로 채우면 부품의 패드가 전부 한 점에 뭉친다. 그러면 이
        # 함수는 "이 부품의 모든 핀이 같은 물리 그룹" 이라고 답하는데, 그건 복원이
        # 아니라 지어낸 것이다. 그 답을 받아 쓴 도메인 추론이 IC 를 "레일+GND 동거"
        # 로 보고 5V 부품이라 판정했고, 남의 보드에서 R12 오탐 2건이 됐다.
        if not getattr(self.netlist, "HAS_COORDINATES", True):
            return {}

        pads = [
            (coord[0] if coord[0] is not None else 0.0, pin, net)
            for (_r, pin, coord), net in self.part_pins.get(ref, {}).items()
        ]
        if not pads:
            return {}

        pads.sort(key=lambda t: t[0])
        groups: "dict[float, list[tuple[str, str]]]" = {}
        anchor = pads[0][0]
        previous = anchor
        for x, pin, net in pads:
            if x - previous > PAD_CLUSTER_GAP_INCH:
                anchor = x
            groups.setdefault(anchor, []).append((pin, net))
            previous = x
        return groups

    # ------------------------------------------------------------------ 추론

    def _supply_domain(self, ref: str) -> Domain:
        named = self.pins_of(ref)

        # 0. 어느 모듈인지 알면 **칩이 로직 전압을 말해 준다.** 배선보다 이게 세다.
        #
        #    개발보드는 `5V` 핀과 `3V3` 핀을 둘 다 뽑는다. 하나는 레귤레이터 입력이고
        #    하나는 출력이라, 배선만 보고 고르면 절반은 틀린다. 실제로 우리 보드의
        #    XIAO 가 REV2 에서 3V3 핀을 떼자 **5V 부품으로 판정됐다** — 3.3V 로직인데.
        chip_v = self._chip_logic_volts(ref)
        if chip_v is not None:
            return Domain(chip_v, f"{ref} = {self._chip_name(ref)} (칩 로직 전압)", CONFIDENCE_HIGH)

        # 1. `VDDIO` 는 **부품이 스스로 밝힌 IO 공급핀**이다. 다른 레일이 있어도 이게 맞다.
        #    코어와 IO 를 다른 전압으로 도는 부품이 실제로 그렇게 그려진다.
        for pin, nets in named.items():
            if IO_SUPPLY_PIN_PATTERN.match(pin):
                for n in nets:
                    v = volts(n)
                    if v:
                        return Domain(v, f"{ref}.{pin} → {n}", CONFIDENCE_HIGH)

        # 2. 나머지 전원 핀. **두 패턴을 합쳐서 본다.**
        #
        #    따로 보면 안 된다 — `3V3` 를 먼저 훑고 거기서 반환해 버리면 옆에 있는
        #    `5V` 핀을 아예 못 본다. Mega Pro(ATmega2560, **5V 로직**)가 정확히 그 모양이라
        #    3.3V 보드로 읽혔고, 거기 붙은 5V 부품이 전부 오탐이 됐다 —
        #    홀드아웃 보드 하나에서 7건. `3V3` 는 IO 선언이 아니라 **레귤레이터 출력 핀**이다.
        #
        #    전압이 다른 전원 핀이 둘 이상이면 어느 쪽이 로직인지 넷리스트가 안 말해 준다.
        #    모르면 모른다고 한다 (헌법 2-2). 아는 부품은 위 0단계가 이미 잡았다.
        #    단, `VIN`·`VBUS` 는 이름이 이미 **먹는 쪽**이라고 말한다. 다른 전원 핀이
        #    있으면 투표에서 뺀다 — 안 그러면 `VIN→5V` + `3V3→3V3` 인 레귤레이터 내장
        #    부품이 전부 "모른다" 가 된다. 그것뿐이면 그건 써야 한다 (센서 다수가 그렇다).
        rails: list[tuple[str, str, float]] = []
        inputs: list[tuple[str, str, float]] = []
        for pin, nets in named.items():
            if not (IO_RAIL_PIN_PATTERN.match(pin) or SUPPLY_PIN_PATTERN.match(pin)):
                continue
            bucket = inputs if SUPPLY_INPUT_PIN_PATTERN.match(pin) else rails
            for n in sorted(nets):
                v = volts(n)
                if v:
                    bucket.append((pin, n, v))
        found = rails or inputs
        distinct = {v for _p, _n, v in found}
        if len(distinct) == 1:
            pin, n, v = found[0]
            return Domain(v, f"{ref}.{pin} → {n}", CONFIDENCE_HIGH)
        if len(distinct) > 1:
            shown = " · ".join(sorted(f"{p}→{n}" for p, n, _v in found))
            return Domain(
                None,
                f"{ref} 에 전압이 다른 전원 핀이 둘 이상 있습니다 ({shown}) — "
                f"어느 쪽이 IO 로직 전압인지 넷리스트만으로는 알 수 없습니다",
                CONFIDENCE_NONE,
            )

        # 3. 이름 없는 패드뿐이면 (K1 의 'pad-'),
        #    전원+접지가 같이 들어 있는 X클러스터에서 레일을 읽는다.
        for gx, members in self.clusters(ref).items():
            rails = [volts(n) for _p, n in members if volts(n) and not GND_PATTERN.match(local_name(n))]
            has_gnd = any(GND_PATTERN.match(local_name(n)) for _p, n in members)
            # **레일이 둘 이상이면 어느 쪽이 IO 전압인지 모른다.** 5V 를 받아 3.3V 로
            # 도는 모듈이 그렇다. 높은 쪽을 고르면 그 부품에서 나가는 신호 네트가
            # 전부 오탐이 된다 — 실보드에서 21건 났다. 모르면 모른다고 한다 (헌법 2-2).
            if len(set(rails)) > 1:
                continue
            if rails and has_gnd:
                return Domain(
                    max(rails),
                    f"{ref} 패드 클러스터 @X{gx:+.4f} (레일+GND 동거)",
                    CONFIDENCE_INFERRED,
                )

        # 4. 이름 있는 전원 핀도 패드 클러스터도 실패했다.
        #    **이 부품이 어느 레일에 닿아 있는지**로 마지막 추론을 한다 (요청서 A+1).
        #    KiCad 넷리스트는 핀 이름이 숫자(`1` · `2`)라 1~3단계가 전부 빗나간다.
        #    전압을 아는 레일이 **정확히 하나**일 때만 쓴다. 둘이면 어느 쪽이 IO 인지 모른다.
        nets_of = list(self.part_pins.get(ref, {}).values())
        rails = {
            n
            for n in set(nets_of)
            if volts(n) and not GND_PATTERN.match(local_name(n)) and self.is_power_rail(n)
        }
        touches_ground = any(GND_PATTERN.match(local_name(n)) for n in nets_of)

        # **"이 부품은 그 레일에서 전원을 받는다" 는 부품이 작을 때만 믿을 만하다.**
        #
        # 40핀 라즈베리파이 헤더가 +5V 와 GND 에 닿는다는 이유로 5V 부품이 됐고,
        # 거기 물린 3.3V 마이크가 전부 "5V 가 3.3V 를 직결" 로 떴다 — 한 보드에서 10건.
        # 헤더의 나머지 36핀은 전부 3.3V 신호다. R11 은 이 전제를 이미 막고 있었는데
        # (「커넥터는 핀마다 다른 신호를 나른다」) R12 는 안 막고 있었다.
        #
        # 핀 개수로 자르지 않고 **비율로** 본다 — 2핀 저항은 100%, 3핀 센서는 67%,
        # 40핀 헤더는 10% 다. 개수는 부품마다 다르지만 비율은 성질을 말한다.
        power_pins = sum(
            1 for n in nets_of
            if GND_PATTERN.match(local_name(n)) or (volts(n) and self.is_power_rail(n))
        )
        mostly_power = nets_of and power_pins / len(nets_of) >= RAIL_INFERENCE_MIN_POWER_SHARE

        if len(rails) == 1 and touches_ground and mostly_power:
            rail = rails.pop()
            return Domain(volts(rail), f"{ref} → {rail} (레일 소속)", CONFIDENCE_INFERRED)

        return Domain(None, "unknown", CONFIDENCE_NONE)

    # ------------------------------------------------------------------ 네트 분류

    def is_power_rail(self, net: str) -> bool:
        """이 네트가 전원 레일인가.

        **이름만으로 판단하지 않는다.** 이름은 양쪽으로 틀린다 —
        `+VSW` · `V_LDO` 는 전원인데 전압 토큰이 없고, `PRESENCE_3V3` 는 신호인데 있다.
        토폴로지가 말해 주는 것을 먼저 본다.

        1. 공급 핀(`VCC`·`VDD`…)이 **둘 이상** 붙어 있다 — 여러 부품이 여기서 전원을 받는다
        2. **접지로 가는 커패시터**가 있고 이름도 레일이라고 말한다 — 디커플링이다
        3. 이름이 레일 같고 팬아웃이 넓다 (기존 판정)

        1·2 는 이름이 없어도 서고, 3 은 이름에 기댄다. 셋 다 아니면 신호다.
        """
        if GND_PATTERN.match(local_name(net)):
            return True

        pads = [p for p in self.netlist.nets.get(net, []) if not p.is_via]
        refs = {p.ref for p in pads}

        # **핀 *이름* 을 본다. 번호가 아니다.**
        #
        # `p.pin` 은 회로도 넷리스트에서 핀 *번호*(`15`)다. 거기다 `VCC|VDD|VIN…` 패턴을
        # 대면 하나도 안 걸려서 전원 레일이 통째로 신호로 분류된다. 그러면 R11·R12 가
        # 전원 레일 위에서 돈다 — 실보드 오탐의 한 갈래가 이것이었다.
        # `pins_of()` 에서 이미 한 번 고친 것과 **같은 버그**가 여기 남아 있었다.
        if (
            sum(1 for p in pads if SUPPLY_PIN_PATTERN.match((p.name or p.pin or "")))
            >= SUPPLY_PINS_MIN
        ):
            return True

        named = bool(volts(net) or POWER_NAME_PATTERN.match(local_name(net)))
        if named and self._decoupled(net, refs):
            return True

        return named and len(refs) > POWER_RAIL_FANOUT_MIN

    def _decoupled(self, net: str, refs: "set[str]") -> bool:
        """이 네트와 접지 사이에 커패시터가 있는가. 전원 레일의 서명이다."""
        for ref in refs:
            if not PASSIVE_REF_PATTERN.match(ref) or not ref.startswith("C"):
                continue
            if any(GND_PATTERN.match(local_name(o)) for o in self.other_nets(ref, net)):
                return True
        return False

    def signal_nets(self) -> "OrderedDict[str, list[Pad]]":
        """판정 대상 네트. 접지와 전원 레일은 뺀다."""
        out: "OrderedDict[str, list[Pad]]" = OrderedDict()
        for net, pads in self.netlist.nets.items():
            if not net or net == NO_CONNECT:
                continue
            if GND_PATTERN.match(local_name(net)):
                continue
            if self.is_power_rail(net):
                continue  # 전원 레일은 신호가 아니다
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
            if GND_PATTERN.match(local_name(other)):
                return PassiveRole(ROLE_PULLDOWN, other, f"{other} 로 끌어내리는 풀다운")

        for other in others:
            v = volts(other)
            if v is not None:
                return PassiveRole(ROLE_PULLUP, other, f"{other} 로 끌어올리는 풀업")

        other = others[0]
        return PassiveRole(ROLE_BRANCH, other, f"{other} 로 이어지는 분기")
