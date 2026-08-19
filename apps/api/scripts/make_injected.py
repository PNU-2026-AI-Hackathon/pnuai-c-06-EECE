"""결함 주입 데이터셋 생성기 (E-2).

**왜 합성인가.** 오탐율을 재려면 "결함이 없다"가 확실한 보드가 필요하다.
실제 오픈소스 보드는 결함이 있는지 없는지 우리가 모른다 — 그걸 아는 것이
E-1(커밋 라벨링)이고 아직 없다. 합성 보드는 우리가 만들었으니 정답을 안다.

**짝으로 만든다.** 규칙마다 결함이 있는 보드와, 겉모습이 비슷한데 정상인 보드를
같이 둔다. 정상 쪽에서 경고가 뜨면 그게 오탐이다 — 그 숫자가 이 데이터셋의 목적이다.

    python scripts/make_injected.py    # 픽스처를 다시 뽑는다
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "injected"

RECORD_SMT = "327"


def rec(net: str, ref: str, pin: str = "", x: float = 0.0, y: float = 0.0) -> str:
    """IPC-D-356 레코드 한 줄. 실측 오프셋(CLAUDE.md 5절)을 그대로 쓴다."""
    line = RECORD_SMT + net.ljust(14)[:14] + " " * 3 + ref.ljust(6)[:6] + "-" + pin.ljust(4)[:4]
    line = line.ljust(41)
    line += f"X{'+' if x >= 0 else '-'}{abs(int(round(x * 10000))):06d}"
    line += f"Y{'+' if y >= 0 else '-'}{abs(int(round(y * 10000))):06d}"
    return line


def board(*lines: str) -> str:
    return "P  CODE 00\nP  UNITS CUST 0\n" + "\n".join(lines) + "\n999\n"


# ── 케이스 정의 ─────────────────────────────────────────────────────
#
# `expect` 는 **정확히** 그 규칙들만 떠야 한다는 뜻이다. 다른 게 뜨면 오탐이다.

SENSOR_5V, MCU = "FAKE-SENSOR-5V", "FAKE-MCU-3V3"
BOM = f"Reference,MPN\nU2,{SENSOR_5V}\nU1,{MCU}\n"

FACTS = [
    {
        "mpn": SENSOR_5V,
        "source_url": "https://example.invalid/sensor.pdf",
        "source_tier": "official",
        "facts": [{"field": "io_level", "value": 5.0, "unit": "V",
                   "table": "Electrical Characteristics", "page": 2,
                   "quote": "IO level 5V", "confidence": "high"}],
    },
    {
        "mpn": MCU,
        "source_url": "https://example.invalid/mcu.pdf",
        "source_tier": "official",
        "facts": [{"field": "vin_absolute_max", "value": 3.6, "unit": "V",
                   "table": "Absolute Maximum Ratings", "page": 5,
                   "quote": "Allowed input voltage 3.6 V", "confidence": "high"}],
    },
]

FIRMWARE_USES_D2 = "const int SENSOR_PIN = D2;\nvoid setup() { pinMode(SENSOR_PIN, INPUT); }\n"
FIRMWARE_USES_D4 = "const int SENSOR_PIN = D4;\nvoid setup() { pinMode(SENSOR_PIN, INPUT); }\n"

CASES: list[dict] = [
    # ── R12 상위 도메인이 하위를 직결 ──
    {
        "id": "r12-cross-domain",
        "kind": "양성",
        "why": "5V 로 도는 U2 의 출력이 3.3V 로 도는 U1 핀에 직결됐다",
        # R11 은 근거가 R12 와 같아서 합쳐진다 (engine.dedupe).
        "expect": ["R12"],
        "netlist": board(
            rec("5V_BUS", "U2", "VCC"), rec("5V_BUS", "C1", "P1", x=0.1),
            rec("5V_BUS", "C2", "P1", x=0.2), rec("5V_BUS", "J1", "VBUS", x=0.3),
            rec("PRESENCE_3V3", "U2", "OUT", y=0.1),
            rec("3V3", "U1", "3V3", x=0.5), rec("3V3", "C3", "P1", x=0.6),
            rec("3V3", "C4", "P1", x=0.7), rec("3V3", "R9", "P1", x=0.8),
            rec("PRESENCE_3V3", "U1", "D2", x=0.5, y=0.1),
        ),
    },
    {
        "id": "r12-same-domain",
        "kind": "음성",
        "why": "겉모습은 같은데 둘 다 3.3V 다. 경고가 뜨면 오탐이다",
        "expect": [],
        "netlist": board(
            rec("3V3", "U2", "VCC"), rec("3V3", "C1", "P1", x=0.1),
            rec("3V3", "C2", "P1", x=0.2), rec("3V3", "J1", "VBUS", x=0.3),
            rec("PRESENCE_3V3", "U2", "OUT", y=0.1),
            rec("3V3", "U1", "3V3", x=0.5),
            rec("PRESENCE_3V3", "U1", "D2", x=0.5, y=0.1),
        ),
    },
    # ── R11 네트명이 주장하는 전압 ≠ 소스 도메인 ──
    {
        "id": "r11-name-lies",
        "kind": "양성",
        "why": "네트 이름은 3V3 인데 구동하는 U2 는 5V 로 돈다",
        "expect": ["R12"],
        "netlist": board(
            rec("5V_BUS", "U2", "VCC"), rec("5V_BUS", "C1", "P1", x=0.1),
            rec("5V_BUS", "C2", "P1", x=0.2), rec("5V_BUS", "J1", "VBUS", x=0.3),
            rec("SIG_3V3", "U2", "OUT", y=0.1),
            rec("3V3", "U1", "3V3", x=0.5), rec("3V3", "C3", "P1", x=0.6),
            rec("3V3", "C4", "P1", x=0.7), rec("3V3", "R9", "P1", x=0.8),
            rec("SIG_3V3", "U1", "D2", x=0.5, y=0.1),
        ),
    },
    {
        "id": "r11-name-honest",
        "kind": "음성",
        "why": "이름과 도메인이 맞다. 이름에 전압 토큰이 있다고 경고하면 오탐이다",
        "expect": [],
        "netlist": board(
            rec("3V3", "U2", "VCC"), rec("3V3", "C1", "P1", x=0.1),
            rec("3V3", "C2", "P1", x=0.2), rec("3V3", "J1", "VBUS", x=0.3),
            rec("SIG_3V3", "U2", "OUT", y=0.1),
            rec("3V3", "U1", "3V3", x=0.5),
            rec("SIG_3V3", "U1", "D2", x=0.5, y=0.1),
        ),
    },
    # ── R04 출력이 절대 최대 정격 초과 ──
    {
        "id": "r04-overvoltage",
        "kind": "양성",
        "why": "U2 출력 5V 가 U1 절대 최대 3.6V 를 넘는다. 양쪽 데이터시트가 있다",
        # R12 는 넷리스트 근거뿐이라 데이터시트 근거를 든 R04 로 합쳐진다.
        "expect": ["R04"],
        "bom": BOM,
        "facts": FACTS,
        "netlist": board(
            rec("5V_BUS", "U2", "VCC"), rec("5V_BUS", "C1", "P1", x=0.1),
            rec("5V_BUS", "C2", "P1", x=0.2), rec("5V_BUS", "J1", "VBUS", x=0.3),
            rec("SIG_3V3", "U2", "OUT", y=0.1),
            rec("3V3", "U1", "3V3", x=0.5), rec("3V3", "C3", "P1", x=0.6),
            rec("3V3", "C4", "P1", x=0.7), rec("3V3", "R9", "P1", x=0.8),
            rec("SIG_3V3", "U1", "D2", x=0.5, y=0.1),
        ),
    },
    {
        "id": "r04-within-limit",
        "kind": "음성",
        "why": "같은 배선인데 U2 출력이 3.3V 다. 한도 안이므로 R04 는 조용해야 한다",
        "expect": [],
        "bom": BOM,
        "facts": [
            {**FACTS[0], "facts": [{**FACTS[0]["facts"][0], "value": 3.3,
                                    "quote": "IO level 3.3V"}]},
            FACTS[1],
        ],
        "netlist": board(
            rec("3V3", "U2", "VCC"), rec("3V3", "C1", "P1", x=0.1),
            rec("3V3", "C2", "P1", x=0.2), rec("3V3", "J1", "VBUS", x=0.3),
            rec("SIG_3V3", "U2", "OUT", y=0.1),
            rec("3V3", "U1", "3V3", x=0.5),
            rec("SIG_3V3", "U1", "D2", x=0.5, y=0.1),
        ),
    },
]


# ── R01 코드가 이 칩에서 쓸 수 없는 핀을 사용 ──
#
# 시연 보드(XIAO)는 스트래핑·플래시 핀을 하나도 안 뽑아서 여기 안 걸린다.
# 그래서 맨칩 설계로 만든다 — 패드 이름이 곧 핀 이름인 경우.

C6_BOM = "Reference,MPN\nU1,ESP32-C6-WROOM-1\n"


def plain_pins(chip_id: str) -> "list[int]":
    """이 칩의 표에 **아무 데도 안 걸린** GPIO.

    곁가지 핀(패드 수를 채우려고 넣는 핀)은 여기서 골라야 한다.
    손으로 고르면 틀린다 — 세 번 틀렸다. GPIO9 는 스트래핑, GPIO8 은 구형 플래시,
    GPIO16 은 C6 UART TX 였다. 칩 표가 자라면 어제의 평범한 핀이 오늘 특별해진다.
    """
    from prefab.chips import CHIPS

    c = CHIPS[chip_id]
    taken = set(c.input_only) | set(c.spi_flash) | set(c.strapping) | set(c.boot_output)
    taken |= set(c.adc1) | set(c.adc2)
    return [g for g in range(31) if g not in taken]


#: 곁가지로 쓸 깨끗한 핀. 표에서 계산하므로 표가 자라면 같이 움직인다.
C6_PLAIN = plain_pins("esp32c6")


def bare(*pins: str) -> str:
    """맨칩 패드. 최소 4개는 있어야 칩으로 인정한다 (커넥터 오인 방지).

    **각 네트에 상대 패드를 붙인다.** 패드 하나뿐인 네트는 미연결이고
    (`Netlist.is_dangling`), 그러면 R07 이 정당하게 뜬다. 실제로 그렇게 만들었다가
    측정에서 오탐 40%로 잡혔다 — 규칙이 아니라 픽스처가 틀렸다.
    """
    lines = []
    for i, p in enumerate(pins):
        net = f"NET_{p}"
        lines.append(rec(net, "U1", p, x=0.1 * i))
        lines.append(rec(net, "J1", str(i + 1), x=0.1 * i, y=0.5))
    return board(*lines)


def sketch(*gpios: int) -> str:
    """배선된 핀을 **전부** 쓰는 코드.

    일부만 쓰면 나머지에서 R08(배선했는데 코드가 안 씀)이 정당하게 뜬다.
    이 케이스가 재려는 건 R01 이므로 다른 규칙이 끼어들지 않게 한다.
    """
    setup = "\n".join(f"  pinMode({g}, OUTPUT);" for g in gpios)
    loop = "\n".join(f"  digitalWrite({g}, HIGH);" for g in gpios)
    return f"void setup() {{\n{setup}\n}}\nvoid loop() {{\n{loop}\n}}\n"


CASES += [
    {
        "id": "r01-flash-pin",
        "kind": "양성",
        # R02 도 같이 뜬다. 배선(R02)과 사용(R01)이 둘 다 사실이라 억지로 하나만
        # 남기지 않는다. 화면에서 어떻게 묶을지는 별개 문제다 (핀 단위 dedup 미구현).
        "why": "코드가 GPIO24 를 쓰고 회로도도 그 핀을 뽑아놨다. C6 내장 플래시 전용이다",
        "expect": ["R01", "R02"],
        "bom": C6_BOM,
        "firmware": sketch(2, 3, 7, 24),
        "netlist": bare("IO2", "IO3", "IO7", "IO24"),
    },
    {
        "id": "r01-strapping-pin",
        "kind": "양성",
        "why": "코드가 GPIO8 을 쓴다. C6 스트래핑이라 부팅 모드가 흔들릴 수 있다",
        "expect": ["R01"],
        "bom": C6_BOM,
        "firmware": sketch(2, 3, 7, 8),
        "netlist": bare("IO2", "IO3", "IO7", "IO8"),
    },
    {
        "id": "r01-ordinary-pin",
        "kind": "음성",
        "why": "같은 모양인데 표에 없는 핀만 쓴다. 조용해야 한다",
        "expect": [],
        "bom": C6_BOM,
        # 표에 걸린 핀을 피한다 — GPIO9 는 스트래핑, GPIO16 은 UART TX 다.
        "firmware": sketch(2, 3, 7, 18),
        "netlist": bare("IO2", "IO3", "IO7", "IO18"),
    },
    {
        "id": "r01-unknown-chip",
        "kind": "음성",
        "why": "부품번호가 없어 칩을 모른다. 추측해서 경고하면 그게 오탐이다",
        "expect": [],
        "bom": "Reference,MPN\nU1,\n",
        "firmware": sketch(2, 3, 7, 24),
        "netlist": bare("IO2", "IO3", "IO7", "IO24"),
    },
]


# ── R05 이 칩이 지원하지 않는 주변장치 조합 ──

ESP32_BOM = "Reference,MPN\nU1,ESP32-D0WD-V3\n"


def analog(*gpios: int, wifi: bool = False) -> str:
    """배선된 핀을 전부 아날로그로 읽는 코드."""
    head = "#include <WiFi.h>\n" if wifi else ""
    body = "\n".join(f"  analogRead({g});" for g in gpios)
    return f"{head}void setup() {{}}\nvoid loop() {{\n{body}\n}}\n"


CASES += [
    {
        "id": "r05-adc2-with-wifi",
        "kind": "양성",
        "why": "구형 ESP32 에서 ADC2(GPIO25)와 WiFi 를 같이 쓴다. 읽기가 실패한다",
        "expect": ["R05"],
        "bom": ESP32_BOM,
        "firmware": analog(25, 32, 18, 17, wifi=True),
        "netlist": bare("IO25", "IO32", "IO18", "IO17"),
    },
    {
        "id": "r05-adc2-without-wifi",
        "kind": "음성",
        "why": "같은 핀인데 WiFi 를 안 쓴다. 핀만 보고 경고하면 오탐이다",
        "expect": [],
        "bom": ESP32_BOM,
        "firmware": analog(25, 32, 18, 17),
        "netlist": bare("IO25", "IO32", "IO18", "IO17"),
    },
    {
        "id": "r05-adc-strapping-overlap",
        "kind": "양성",
        "why": "C6 의 GPIO4 는 ADC 채널이면서 스트래핑이다. 부팅이 흔들릴 수 있다",
        # R01 도 같이 뜬다 — GPIO4 는 스트래핑 핀이니 둘 다 사실이다.
        # dedup 은 네트 단위라 핀 단위 발견(net=None)은 안 묶인다. 열린 항목이다.
        "expect": ["R01", "R05"],
        "bom": C6_BOM,
        "firmware": analog(4, 2, 18, 17),
        "netlist": bare("IO4", "IO2", "IO18", "IO17"),
    },
    {
        "id": "r05-adc-no-overlap",
        "kind": "음성",
        "why": "같은 모양인데 겹치지 않는 ADC 채널만 쓴다",
        "expect": [],
        "bom": C6_BOM,
        "firmware": analog(2, 3, 18, 17),
        "netlist": bare("IO2", "IO3", "IO18", "IO17"),
    },
]



# ── R02 회로도가 SPI 플래시 전용 핀에 배선 ──
#
# 시연 보드는 플래시 핀을 안 뽑아놔서 여기 안 걸린다. 맨칩 설계로 만든다.
# **음성 케이스가 중요하다** — 맨칩에서 플래시 핀이 진짜 플래시 IC 로 가는 것은
# 정상 설계다. 그것까지 잡으면 맨칩 보드마다 오탐이 난다.

FLASH_IO = ("IO24", "IO25", "IO26", "IO27")   # C6 내장 플래시 전용 (GPIO24~30)


def flash_to_device(*extra: str) -> str:
    """플래시 핀 4가닥이 한 IC(U9)로 간다. 정상 설계다."""
    lines = []
    for i, pin in enumerate(FLASH_IO):
        net = f"FLASH_{pin}"
        lines.append(rec(net, "U1", pin, x=0.1 * i))
        lines.append(rec(net, "U9", str(i + 1), x=0.1 * i, y=0.6))
    for j, pin in enumerate(extra):
        net = f"NET_{pin}"
        lines.append(rec(net, "U1", pin, x=0.1 * (j + 9)))
        lines.append(rec(net, "J1", str(j + 1), x=0.1 * (j + 9), y=0.5))
    return board(*lines)


CASES += [
    {
        "id": "r02-flash-pin-wired",
        "kind": "양성",
        "why": "GPIO24 가 LED 커넥터로 빠졌다. C6 에서 내장 플래시 전용이라 부팅이 실패한다",
        "expect": ["R02"],
        "bom": C6_BOM,
        "netlist": bare("IO2", "IO3", "IO18", "IO24"),
    },
    {
        "id": "r02-external-flash",
        "kind": "음성",
        "why": "플래시 핀 4가닥이 전부 한 IC 로 간다. 이건 플래시 IC 다. 경고가 뜨면 오탐이다",
        "expect": [],
        "bom": C6_BOM,
        "netlist": flash_to_device("IO2", "IO3", "IO18"),
    },
    {
        "id": "r02-no-flash-pin",
        "kind": "음성",
        "why": "같은 모양인데 플래시 핀을 안 건드린다. 조용해야 한다",
        "expect": [],
        "bom": C6_BOM,
        "netlist": bare("IO2", "IO3", "IO18", "IO17"),
    },
]


# ── R03 스트래핑 핀이 전원·접지에 직결 ──
#
# 저항·스위치를 거치면 그 패드는 다른 네트에 있으므로 안 걸린다. 그게 맞다 —
# 풀업 저항과 부트 버튼은 정상 설계이고 그것까지 잡으면 거의 모든 보드에서 오탐이다.

STRAP = "IO8"   # C6 스트래핑 (GPIO4·5·8·9·15)


def tied(pin: str, rail: str, *others: str) -> str:
    """한 핀을 레일에 직결하고 나머지는 평범하게 뺀다."""
    lines = [rec(rail, "U1", pin, x=0.0), rec(rail, "C1", "2", x=0.0, y=0.4)]
    for i, p in enumerate(others):
        net = f"NET_{p}"
        lines.append(rec(net, "U1", p, x=0.1 * (i + 1)))
        lines.append(rec(net, "J1", str(i + 1), x=0.1 * (i + 1), y=0.5))
    return board(*lines)


def through_resistor(pin: str, rail: str, *others: str) -> str:
    """스트래핑 핀 → 저항 → 레일. 패드는 레일이 아니라 중간 네트에 있다."""
    lines = [
        rec("STRAP_PU", "U1", pin, x=0.0),
        rec("STRAP_PU", "R9", "1", x=0.0, y=0.4),
        rec(rail, "R9", "2", x=0.0, y=0.8),
        rec(rail, "C1", "2", x=0.1, y=0.8),
    ]
    for i, p in enumerate(others):
        net = f"NET_{p}"
        lines.append(rec(net, "U1", p, x=0.1 * (i + 1)))
        lines.append(rec(net, "J1", str(i + 1), x=0.1 * (i + 1), y=0.5))
    return board(*lines)


CASES += [
    {
        "id": "r03-strapping-tied-gnd",
        "kind": "양성",
        "why": "GPIO8 이 GND 에 직결됐다. C6 스트래핑이라 부팅 모드가 한쪽으로 굳는다",
        "expect": ["R03"],
        "bom": C6_BOM,
        "netlist": tied(STRAP, "GND", "IO2", "IO3", "IO18"),
    },
    {
        "id": "r03-strapping-pullup",
        "kind": "음성",
        "why": "같은 핀인데 저항을 거친다. 풀업은 정상 설계다. 경고가 뜨면 오탐이다",
        "expect": [],
        "bom": C6_BOM,
        "netlist": through_resistor(STRAP, "3V3", "IO2", "IO3", "IO18"),
    },
    {
        "id": "r03-ordinary-pin-tied",
        "kind": "음성",
        "why": "스트래핑이 아닌 GPIO18 이 GND 에 묶였다. 표에 없는 핀이므로 조용해야 한다",
        "expect": [],
        "bom": C6_BOM,
        "netlist": tied("IO18", "GND", "IO2", "IO3", "IO17"),
    },
]



# ── R09 부팅 중 출력이 나오는 핀에 부하 연결 ──
#
# 등급이 `정보` 다. 개발 보드는 거의 전부 TX 를 뽑아놓으므로 경고로 올리면 시끄럽다.
# 넷리스트만으로는 붙은 게 브리지인지 릴레이인지 모른다. 사실만 알린다.

BOOT_TX = "IO16"   # C6 U0TXD


def peered(*pairs: "tuple[str, str]") -> str:
    """(패드, 상대부품) 목록으로 맨칩 보드를 만든다."""
    lines = []
    for i, (pin, peer) in enumerate(pairs):
        net = f"NET_{pin}"
        lines.append(rec(net, "U1", pin, x=0.1 * i))
        lines.append(rec(net, peer, "1", x=0.1 * i, y=0.5))
    return board(*lines)


CASES += [
    {
        "id": "r09-boot-output-load",
        "kind": "양성",
        "why": "GPIO16(U0TXD)에 릴레이가 붙었다. 부팅 로그가 매 부팅마다 그리로 나간다",
        "expect": ["R09"],
        "bom": C6_BOM,
        "netlist": peered((BOOT_TX, "K1"), ("IO2", "J1"), ("IO3", "J1"), ("IO17", "J1")),
    },
    {
        "id": "r09-no-boot-pin",
        "kind": "음성",
        "why": "같은 모양인데 TX 를 안 뽑았다. 조용해야 한다",
        "expect": [],
        "bom": C6_BOM,
        "netlist": peered(("IO2", "J1"), ("IO3", "J1"), ("IO17", "J1"), ("IO18", "J1")),
    },
]


# ── R09 부팅 시 출력 나오는 핀에 부하 연결 ──
#
# C6 는 GPIO16(U0TXD)만 출처가 확실하다 — 부팅 로그가 115200bps 로 나간다.
# **음성 케이스가 이 규칙의 전부다.** 같은 핀을 헤더(J1)로 빼는 것은 시리얼 콘솔이고
# 정상 설계다. 그것까지 잡으면 거의 모든 개발보드에서 오탐이 난다.

BOOT_TX = "IO16"          # C6 U0TXD
RELAY_BOM = "Reference,MPN\nU1,ESP32-C6-WROOM-1\nK1,JQC-3FF-S-Z\n"


def driven_by(pin: str, load_ref: str, load_pin: str, *others: str) -> str:
    """한 핀을 구동 부품에 직결하고 나머지는 평범하게 뺀다."""
    lines = [
        rec("CTRL", "U1", pin, x=0.0),
        rec("CTRL", load_ref, load_pin, x=0.0, y=0.4),
    ]
    for i, p in enumerate(others):
        net = f"NET_{p}"
        lines.append(rec(net, "U1", p, x=0.1 * (i + 1)))
        lines.append(rec(net, "J1", str(i + 1), x=0.1 * (i + 1), y=0.5))
    return board(*lines)


CASES += [
    {
        "id": "r09-boot-tx-drives-relay",
        "kind": "양성",
        "why": "릴레이 IN 이 GPIO16(U0TXD)에 직결됐다. 전원을 넣을 때마다 부팅 로그로 딸깍거린다",
        "expect": ["R09"],
        "bom": RELAY_BOM,
        "netlist": driven_by(BOOT_TX, "K1", "IN", "IO2", "IO3", "IO17"),
    },
    {
        "id": "r09-boot-tx-to-header",
        "kind": "음성",
        "why": "같은 핀인데 커넥터로 뺐다. 시리얼 콘솔은 정상 설계다. 경고가 뜨면 오탐이다",
        "expect": [],
        "bom": C6_BOM,
        "netlist": bare("IO2", "IO3", "IO17", BOOT_TX),
    },
    {
        "id": "r09-ordinary-pin-drives-relay",
        "kind": "음성",
        "why": "같은 릴레이인데 부팅 때 조용한 GPIO2 가 몬다. 표에 없는 핀이므로 조용해야 한다",
        "expect": [],
        "bom": RELAY_BOM,
        "netlist": driven_by("IO2", "K1", "IN", "IO3", "IO16", "IO17"),
    },
]


#: 합성이 아닌 유일한 케이스. 실제 보드이고 정답표가 문서로 고정돼 있다
#: (`tests/fixtures/esp32-c6-presence-smart-light.EXPECTED.md`).
#: 합성만으로 재면 "우리가 만든 상황에서만 맞다" 는 소리를 못 벗어난다.
REAL_BOARD = {
    "id": "real-esp32c6-presence",
    "kind": "실측",
    "why": "실제 보드 + 실제 펌웨어. 정답표는 EXPECTED.md 에 고정돼 있다",
    "expect": ["R07", "R08", "R12"],
    "netlist_src": "esp32-c6-presence-smart-light.d356",
    "bom_src": "esp32-c6-presence-smart-light.bom.csv",
    "firmware_src": "esp32-c6-presence-smart-light.firmware",
}


def _link_real(manifest: list[dict]) -> None:
    """실측 픽스처는 복사하지 않고 상대경로로 가리킨다. 두 벌이 되면 갈라진다."""
    manifest.append({
        "id": REAL_BOARD["id"],
        "kind": REAL_BOARD["kind"],
        "why": REAL_BOARD["why"],
        "expect": REAL_BOARD["expect"],
        "netlist": f"../{REAL_BOARD['netlist_src']}",
        "bom": f"../{REAL_BOARD['bom_src']}",
        "firmware": f"../{REAL_BOARD['firmware_src']}",
    })


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case in CASES:
        stem = case["id"]
        (OUT / f"{stem}.d356").write_text(case["netlist"], encoding="utf-8")
        entry = {
            "id": stem,
            "kind": case["kind"],
            "why": case["why"],
            "expect": case["expect"],
            "netlist": f"{stem}.d356",
        }
        if case.get("bom"):
            (OUT / f"{stem}.bom.csv").write_text(case["bom"], encoding="utf-8")
            entry["bom"] = f"{stem}.bom.csv"
        if case.get("firmware"):
            folder = OUT / f"{stem}.firmware"
            folder.mkdir(exist_ok=True)
            (folder / "sketch.ino").write_text(case["firmware"], encoding="utf-8")
            entry["firmware"] = f"{stem}.firmware"
        if case.get("facts"):
            (OUT / f"{stem}.facts.json").write_text(
                json.dumps(case["facts"], ensure_ascii=False, indent=2), encoding="utf-8"
            )
            entry["facts"] = f"{stem}.facts.json"
        manifest.append(entry)

    _link_real(manifest)

    (OUT / "MANIFEST.json").write_text(
        json.dumps({"cases": manifest}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(manifest)}개 케이스 → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
