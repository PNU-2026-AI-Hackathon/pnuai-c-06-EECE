"""왜 아무 말도 못 했는지 (진단).

> **"이상 없음"과 "못 봤음"은 다르다.**

발견이 0건일 때 그게 좋은 소식인지 아무것도 못 본 것인지 지금은 알 수 없다.
파이프라인은 **건너뛴 규칙**은 사유와 함께 싣는다 (`skipped`). 그런데 **돌긴 돌았는데
아무 말도 못 한 규칙**은 화면에 "실행 5개 · 발견 0" 으로만 남는다.

`R02` 는 칩을 모르면 `return []` 한다. 그게 맞다 — 어느 핀이 플래시 전용인지는
칩마다 다르고, 추측해서 경고하면 그게 오탐이다. 하지만 사용자에게는
**"플래시 핀 문제 없음"과 "칩을 몰라서 안 봤음"이 똑같이 보인다.**

## 규칙을 안 건드린다

규칙마다 "왜 조용했는지"를 돌려주게 고치면 12개를 전부 손대야 하고, 그 값이
계약에도 없다. 대신 **판정에 필요한 재료가 무엇이 있고 없는지**를 본다.
재료가 없으면 그 재료를 쓰는 규칙이 조용한 것이고, 그건 엔진 밖에서 알 수 있다.

## 표가 낡지 않게

어느 규칙이 어느 재료를 쓰는지는 `MATERIALS` 에 적혀 있다. 손으로 적은 표는
반드시 낡으므로, `tests/test_diagnose.py` 가 **규칙 모듈의 소스를 읽어서**
대조한다 — `chip_of` 를 부르는 규칙이 칩 항목에 없으면 실패한다.

계약(`docs/API_CONTRACT.md`)은 안 건드린다. 이건 CLI 전용 진단이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import catalog
from .mpn import part_numbers, sources_used
from .text import i_ga

OK, PARTIAL, NONE = "있음", "일부", "없음"


@dataclass(frozen=True)
class Material:
    """판정에 쓰이는 재료 하나."""

    name: str
    state: str
    detail: str
    #: 이 재료가 없으면 조용해지는 규칙들
    silences: tuple[str, ...] = ()

    @property
    def missing(self) -> bool:
        return self.state == NONE


#: 재료 → 그 재료 없이는 아무 말도 못 하는 규칙.
#:
#: **여기 적힌 규칙 ID 는 카탈로그에 있어야 하고, `chip_of` 를 부르는 규칙은
#: 반드시 `chip` 항목에 있어야 한다.** 테스트가 소스를 읽어서 확인한다.
MATERIALS: dict[str, tuple[str, ...]] = {
    "chip": ("R01", "R02", "R03", "R05", "R09"),
    "pinmap": ("R01", "R05", "R07", "R08", "R10"),
    "firmware": ("R01", "R05", "R07", "R08", "R10", "R14"),
    "facts": ("R04",),
}

#: 재료 → 그게 없으면 **조용해지는 게 아니라 시끄러워지는** 규칙.
#:
#: 같은 재료를 봐도 방향이 반대인 규칙이 있다. R08 은 칩을 알면 **USB 전용 핀을
#: 걸러낸다** (`Chip.usb`) — 그 핀은 주변장치가 직접 모니까 코드에 `pinMode` 가
#: 없는 게 정상이다. 칩을 모르면 그 억제가 안 되고 **오탐이 늘어난다.**
#:
#: 이 구분을 안 하면 진단이 "칩을 몰라서 R08 이 조용하다" 고 거꾸로 말한다.
#: 이 표를 처음 손으로 적었을 때 실제로 R08 을 위쪽에 넣을 뻔했고,
#: 소스를 읽는 테스트가 그걸 잡았다.
NOISIER_WITHOUT: dict[str, tuple[str, ...]] = {
    "chip": ("R08",),
}

#: 재료 → 그 재료가 없을 때 늘어나는 오탐이 무엇인지 (사용자에게 보이는 문구)
NOISE_DETAIL: dict[str, str] = {
    "chip": "USB 등 주변장치 전용 핀을 못 걸러내 R08 오탐이 늘 수 있음",
}


@dataclass
class Diagnosis:
    materials: list[Material] = field(default_factory=list)
    ran: list[str] = field(default_factory=list)
    skipped: list[Any] = field(default_factory=list)
    findings: int = 0
    #: 돌았는데 아무 말도 못 한 규칙 → 짐작되는 사유
    silent: "dict[str, str]" = field(default_factory=dict)
    #: 재료가 없어서 **오탐이 늘 수 있는** 자리. 조용해지는 것과 방향이 반대다.
    noisy: list[str] = field(default_factory=list)

    @property
    def confident(self) -> bool:
        """0건을 '이상 없음' 이라고 말해도 되는가.

        재료가 하나라도 비어 있으면 안 된다. 그때의 0건은 '못 봤음' 이다.
        """
        return self.findings == 0 and not self.silent and not any(m.missing for m in self.materials)


def diagnose(analysis) -> Diagnosis:
    """검사 결과에서 **왜 그 결과인지**를 뽑는다. 순수 함수다."""
    from .rules.r01_unusable_pin import chip_of

    netlist, graph = analysis.netlist, analysis.graph
    pinmap = getattr(graph, "pinmap", None)
    firmware = analysis.firmware
    ctx = analysis.context

    chip = chip_of(ctx)
    numbers = part_numbers(netlist, analysis.bom)
    known = [p for p in numbers.values() if p.mpn]
    gpio_pads = list(pinmap.gpio_pads()) if pinmap else []
    facts = analysis.context.datasheet

    has_coords = any(
        pad.x is not None for pads in netlist.nets.values() for pad in pads
    )

    materials = [
        Material(
            "넷리스트", OK if netlist.part_count else NONE,
            f"네트 {netlist.net_count} · 부품 {netlist.part_count}",
        ),
        Material(
            "좌표", OK if has_coords else NONE,
            "패드마다 X·Y 가 있음" if has_coords
            else "회로도 넷리스트에는 좌표가 없음 — 기하 기반 실크 복원이 안 됨",
        ),
        Material(
            "부품번호", OK if known else NONE,
            f"{len(known)}/{len(numbers)}개 확인 ("
            + " · ".join(f"{s} {n}" for s, n in sources_used(numbers).items()) + ")"
            if known else "BOM 도 회로도도 부품번호를 안 실어 줌",
            MATERIALS["chip"],
        ),
        Material(
            "칩 식별", OK if chip else NONE,
            chip.name if chip else "어느 칩인지 모름 — 핀 표를 못 봄",
            MATERIALS["chip"],
        ),
        Material(
            "핀맵", OK if gpio_pads else NONE,
            f"GPIO 패드 {len(gpio_pads)}개" if gpio_pads
            else "실크 라벨 → GPIO 를 하나도 못 확정",
            MATERIALS["pinmap"],
        ),
        Material(
            "펌웨어", OK if firmware and firmware.pins else (PARTIAL if firmware else NONE),
            _firmware_detail(firmware),
            MATERIALS["firmware"],
        ),
        Material(
            "부품 사실", OK if facts and len(facts) else NONE,
            f"{len(facts)}건 읽어 둠" if facts and len(facts)
            else "사실 DB 에 이 부품들이 없음 — 경고를 해제할 근거가 없음",
            MATERIALS["facts"],
        ),
    ]

    return Diagnosis(
        materials=materials,
        ran=list(analysis.engine.ran),
        skipped=list(analysis.engine.skipped),
        findings=len(analysis.engine.findings),
        silent=_silent_rules(analysis, materials),
        noisy=[
            f"{' · '.join(NOISIER_WITHOUT[key])} — {NOISE_DETAIL[key]}"
            for key, name in (("chip", "칩 식별"),)
            if any(m.name == name and m.missing for m in materials)
        ],
    )


def _firmware_detail(firmware) -> str:
    if firmware is None:
        return "미제출 — 차별 규칙이 전부 건너뛰어짐"
    if not firmware.pins:
        return (
            f"소스 {len(firmware.files)}개를 읽었는데 **핀을 하나도 못 풀었음**"
            + (f" · 못 읽은 자리 {len(firmware.unresolved)}곳" if firmware.unresolved else "")
        )
    detail = f"소스 {len(firmware.files)}개 · 핀 {len(firmware.pins)}개 ({' · '.join(firmware.labels)})"
    if firmware.unresolved:
        detail += f" · 못 읽은 자리 {len(firmware.unresolved)}곳"
    return detail


def _silent_rules(analysis, materials: list[Material]) -> "dict[str, str]":
    """돌았는데 발견이 0건인 규칙 → 없는 재료 중 그 규칙이 쓰는 것.

    **짐작이라고 분명히 말한다.** 규칙이 조용한 이유를 스스로 말하게 만든 게
    아니라, 재료가 없으니 조용할 것이라고 밖에서 미루어 본 것이다.
    재료가 다 있는데 조용하면 여기 안 실린다 — 그건 진짜 '이상 없음' 이다.
    """
    spoke = {f.rule for f in analysis.engine.findings}
    out: dict[str, str] = {}
    for rule in analysis.engine.ran:
        if rule in spoke:
            continue
        why = [m.name for m in materials if m.missing and rule in m.silences]
        if why:
            out[rule] = " · ".join(why)
    return out


def format_diagnosis(d: Diagnosis, filename: str = "") -> str:
    """사람이 읽는 진단표."""
    bar = "=" * 74
    out = [bar, f"왜 이 결과인가 — {filename}" if filename else "왜 이 결과인가", bar, ""]

    out.append("재료")
    for m in d.materials:
        mark = {OK: "✅", PARTIAL: "⚠️", NONE: "❌"}[m.state]
        out.append(f"  {mark} {m.name:<10} {m.detail}")
        if m.missing and m.silences:
            out.append(f"       └ 이게 없어서 조용해질 수 있는 규칙: {' · '.join(m.silences)}")
    out.append("")

    out.append("규칙")
    out.append(f"  실행 {len(d.ran)} · 건너뜀 {len(d.skipped)} · 카탈로그 {catalog.TOTAL} · 발견 {d.findings}건")
    for s in d.skipped:
        out.append(f"    건너뜀  {s.rule}  {s.detail}")
    if d.silent:
        out.append("")
        out.append("  돌았는데 아무 말도 못 한 규칙 (짐작되는 사유):")
        for rule, why in sorted(d.silent.items()):
            # 조사를 맞춘다 (헌법 11절). 마지막 재료 이름에 맞춘다.
            out.append(f"    {rule}  {i_ga(why)} 없음")
    if d.noisy:
        out.append("")
        out.append("  재료가 없어서 **오탐이 늘 수 있는** 자리:")
        for line in d.noisy:
            out.append(f"    {line}")
    out.append("")

    out.append(bar)
    if d.findings:
        out.append(f"발견 {d.findings}건. 위 재료가 갖춰진 범위 안에서 본 결과다.")
    elif d.confident:
        out.append("발견 0건이고 **재료가 다 갖춰져 있다.** 이 0건은 '이상 없음' 이다.")
    else:
        missing = [m.name for m in d.materials if m.missing]
        out.append(
            "발견 0건이지만 **'이상 없음'이 아니다.** "
            f"없는 재료: {' · '.join(missing) or '없음'}.\n"
            "이 상태의 0건은 '못 봤음' 에 가깝다 — 위 목록을 채우고 다시 돌려야 한다."
        )
    out.append(bar)
    return "\n".join(out)
