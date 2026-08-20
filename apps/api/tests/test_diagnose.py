"""왜 아무 말도 못 했는지 (진단).

> **"이상 없음"과 "못 봤음"은 다르다.**

이 파일이 지키는 것은 두 가지다.

1. 재료가 비었을 때 **0건을 '이상 없음'이라고 말하지 않는가**
2. 재료↔규칙 표가 **코드보다 낡지 않는가** — 손으로 적은 표는 반드시 낡는다
"""

from __future__ import annotations

from pathlib import Path

from prefab import catalog
from prefab.diagnose import MATERIALS, NOISIER_WITHOUT, diagnose, format_diagnosis
from prefab.firmware import load_directory
from prefab.runner import analyze

FIXTURES = Path(__file__).parent / "fixtures"
REAL = FIXTURES / "esp32-c6-presence-smart-light.d356"
FIRMWARE = FIXTURES / "esp32-c6-presence-smart-light.firmware"
SCHEMATIC = FIXTURES / "schematic-gpio-named.net.xml"
RULES_DIR = Path(__file__).parent.parent / "src" / "prefab" / "rules"


def _run(path: Path, *, firmware: bool = False, bom: bool = False):
    bom_bytes = None
    if bom:
        bom_bytes = (FIXTURES / "esp32-c6-presence-smart-light.bom.csv").read_bytes()
    return analyze(
        path.read_text(encoding="utf-8", errors="replace"),
        filename=path.name,
        bom_bytes=bom_bytes,
        firmware_sources=load_directory(FIRMWARE) if firmware else None,
    )


# ── 0건을 뭐라고 부르는가 ───────────────────────────────────────────


def test_재료가_비면_0건을_이상_없음이라고_안_한다():
    """이게 이 파일의 존재 이유다. 못 본 것을 봤다고 하면 안 된다."""
    d = diagnose(_run(SCHEMATIC))
    assert d.findings == 0
    assert not d.confident
    text = format_diagnosis(d)
    assert "'이상 없음'이 아니다" in text
    assert "못 봤음" in text


def test_없는_재료를_이름으로_말한다():
    """'뭔가 부족합니다' 로는 사용자가 다음에 뭘 할지 모른다."""
    d = diagnose(_run(SCHEMATIC))
    missing = {m.name for m in d.materials if m.missing}
    assert "칩 식별" in missing
    assert "펌웨어" in missing


def test_돌았는데_조용한_규칙을_사유와_함께_적는다():
    """건너뛴 규칙은 파이프라인이 이미 싣는다. 문제는 **돌았는데 조용한** 쪽이다."""
    d = diagnose(_run(SCHEMATIC))
    # R02·R03·R09 는 돌긴 돌았다 (needs 가 netlist 뿐이다)
    assert {"R02", "R03", "R09"} <= set(d.ran)
    # 그런데 칩을 몰라 아무 말도 못 했다
    assert {"R02", "R03", "R09"} <= set(d.silent)
    assert "칩 식별" in d.silent["R02"]


def test_발견이_있으면_범위를_밝힌다():
    """5건을 찾았다고 '전부 봤다'는 뜻이 아니다."""
    text = format_diagnosis(diagnose(_run(REAL, firmware=True, bom=True)))
    assert "발견 5건" in text
    assert "갖춰진 범위 안에서" in text


def test_재료가_다_있으면_조용한_규칙을_안_적는다():
    """재료가 다 있는데 조용한 것은 진짜 '이상 없음' 이다. 사유를 지어내지 않는다."""
    d = diagnose(_run(REAL, firmware=True, bom=True))
    # 이 보드는 사실 DB 가 비어서 R04 만 사유가 붙는다
    assert set(d.silent) <= {"R04"}
    for rule, why in d.silent.items():
        assert why, f"{rule} 에 사유 없이 이름만 실렸다"


# ── 표가 낡지 않는가 ────────────────────────────────────────────────


def test_표의_규칙_ID_가_전부_카탈로그에_있다():
    known = {s.id for s in catalog.CATALOG}
    for material, rules in MATERIALS.items():
        unknown = set(rules) - known
        assert not unknown, f"{material} 에 카탈로그에 없는 규칙: {unknown}"


def test_칩_표를_보는_규칙이_전부_적혀_있다():
    """**소스를 읽어서 대조한다.** 규칙이 늘어도 이 표가 안 낡는다.

    `chip_of` 를 부르는 규칙은 칩을 모르면 조용해진다 — 예외가 없다.
    새 규칙이 그 함수를 쓰는데 표에 없으면 여기서 잡힌다.
    """
    callers = {
        path.stem.split("_")[0].upper()
        for path in RULES_DIR.glob("r*.py")
        if "chip_of(" in path.read_text(encoding="utf-8")
    }
    # 같은 재료를 봐도 **방향이 반대인** 규칙이 있다. R08 은 칩을 모르면
    # 조용해지는 게 아니라 USB 오탐이 늘어난다. 둘 중 하나에는 반드시 있어야 한다.
    listed = set(MATERIALS["chip"]) | set(NOISIER_WITHOUT["chip"])
    missing = callers - listed - {"R01"}  # r01 이 chip_of 를 정의하는 곳이다
    assert not missing, (
        f"chip_of 를 쓰는데 MATERIALS['chip'] 에도 NOISIER_WITHOUT['chip'] 에도 "
        f"없는 규칙: {missing}. 어느 쪽인지 정해서 넣으세요 — "
        "조용해지는지 시끄러워지는지는 사용자에게 정반대의 뜻입니다."
    )


def test_조용해지는_것과_시끄러워지는_것을_안_섞는다():
    """같은 규칙이 양쪽에 있으면 진단이 앞뒤가 안 맞는다."""
    for key, quiet in MATERIALS.items():
        both = set(quiet) & set(NOISIER_WITHOUT.get(key, ()))
        assert not both, f"{key}: {both} 가 조용해짐과 시끄러워짐 양쪽에 있다"


def test_칩을_모르면_오탐이_는다는_것도_말한다():
    """'못 봤음' 만 말하고 '잘못 볼 수 있음' 을 안 말하면 절반만 정직한 것이다."""
    d = diagnose(_run(SCHEMATIC))
    assert d.noisy, "칩을 모르는 보드인데 오탐 경고가 없다"
    assert "R08" in " ".join(d.noisy)
    assert "오탐이 늘 수 있는" in format_diagnosis(d)


def test_펌웨어를_보는_규칙이_전부_적혀_있다():
    callers = {
        path.stem.split("_")[0].upper()
        for path in RULES_DIR.glob("r*.py")
        if "ctx.firmware" in path.read_text(encoding="utf-8")
    }
    missing = callers - set(MATERIALS["firmware"])
    assert not missing, (
        f"ctx.firmware 를 쓰는데 MATERIALS['firmware'] 에 없는 규칙: {missing}"
    )


# ── 순수한가 ────────────────────────────────────────────────────────


def test_같은_입력이면_같은_진단이다():
    a = _run(REAL, firmware=True)
    first, second = diagnose(a), diagnose(a)
    assert [(m.name, m.state) for m in first.materials] == [
        (m.name, m.state) for m in second.materials
    ]
    assert first.silent == second.silent
