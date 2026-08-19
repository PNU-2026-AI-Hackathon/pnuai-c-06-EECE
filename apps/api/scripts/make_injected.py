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
        "expect": ["R11", "R12"],
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
        "expect": ["R11", "R12"],
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
        "expect": ["R04", "R11", "R12"],
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


#: 합성이 아닌 유일한 케이스. 실제 보드이고 정답표가 문서로 고정돼 있다
#: (`tests/fixtures/esp32-c6-presence-smart-light.EXPECTED.md`).
#: 합성만으로 재면 "우리가 만든 상황에서만 맞다" 는 소리를 못 벗어난다.
REAL_BOARD = {
    "id": "real-esp32c6-presence",
    "kind": "실측",
    "why": "실제 보드 + 실제 펌웨어. 정답표는 EXPECTED.md 에 고정돼 있다",
    "expect": ["R07", "R08", "R11", "R12"],
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
