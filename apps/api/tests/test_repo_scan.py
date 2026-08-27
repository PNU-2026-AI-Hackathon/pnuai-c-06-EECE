"""저장소를 훑어 파일을 찾는다.

**이 기능의 최악은 「틀린 경로를 자신 있게 채워 주는 것」이다.**
액션이 "넷리스트를 못 찾았습니다" 로 죽으면 사용자는 우리 도구가 고장 났다고
읽는다 — 자기가 고를 기회조차 없었기 때문이다 (헌법 2-3).

그래서 테스트의 절반이 **「안 고르는지」** 를 본다.
"""

from __future__ import annotations

import pytest

from web import repo

# 실제 오픈소스 하드웨어 저장소에서 흔한 배치들
KICAD_REPO = [
    "README.md",
    "LICENSE",
    "hardware/board.kicad_sch",
    "hardware/board.kicad_pcb",
    "hardware/board.net.xml",
    "hardware/bom.csv",
    "firmware/main/main.ino",
    "firmware/main/config.h",
    "docs/schematic.pdf",
]

PLATFORMIO_REPO = [
    "platformio.ini",
    "src/main.cpp",
    "src/sensor.cpp",
    "src/sensor.h",
    "lib/Adafruit_GFX/Adafruit_GFX.cpp",
    "pcb/export/board.d356",
    "pcb/bom_v3.csv",
]

MESSY_REPO = [
    "readme.txt",
    "notes.txt",
    "config.xml",
    "data/output.csv",
    "sketch.ino",
]


# ------------------------------------------------------------ 넷리스트

def test_전용_확장자를_제일_위로_올린다():
    got = repo.netlist_candidates(PLATFORMIO_REPO)
    assert got[0].path == "pcb/export/board.d356"
    assert got[0].score >= repo.CONFIDENT


def test_회로도_넷리스트도_찾는다():
    got = repo.netlist_candidates(KICAD_REPO)
    assert got[0].path == "hardware/board.net.xml"


def test_남의_코드는_안_본다():
    """`lib/` 안은 남이 쓴 라이브러리다. 후보에 넣으면 목록이 쓰레기가 된다."""
    paths = [c.path for c in repo.firmware_candidates(PLATFORMIO_REPO)]
    assert not any(p.startswith("lib/") for p in paths)


def test_흔한_확장자를_자신있게_고르지_않는다():
    """`config.xml` 과 `readme.txt` 를 넷리스트라고 채워 두면 그게 오탐이다."""
    scan = repo.scan(MESSY_REPO)
    assert scan.to_dict()["netlist"]["picked"] is None


def test_후보로는_남긴다():
    """안 고르는 것과 안 보여주는 것은 다르다. 사용자가 알 수도 있다."""
    got = repo.netlist_candidates(MESSY_REPO)
    assert "config.xml" in [c.path for c in got]


def test_비슷한_후보가_둘이면_우리가_안_고른다():
    """1등과 2등이 붙어 있으면 그건 사람이 아는 것이다."""
    both = ["hw/a.d356", "hw/b.d356"]
    assert repo.Scan(repo.netlist_candidates(both), [], []).to_dict()["netlist"]["picked"] is None


def test_아무것도_없으면_없다고_한다():
    scan = repo.scan(["README.md", "src/index.js"])
    out = scan.to_dict()
    assert out["netlist"]["picked"] is None
    assert out["netlist"]["candidates"] == []


# ------------------------------------------------------------ 펌웨어

def test_펌웨어는_파일이_아니라_폴더를_고른다():
    """액션이 폴더를 받는다. 파일을 주면 그 하나만 올라간다."""
    got = repo.firmware_candidates(KICAD_REPO)
    assert got[0].path == "firmware/main"


def test_아두이노_스케치가_있으면_확신한다():
    got = repo.firmware_candidates(KICAD_REPO)
    assert got[0].score >= repo.CONFIDENT
    assert ".ino" in got[0].reason


# ------------------------------------------------------------ 부품 목록

def test_이름에_bom_이_있는_csv_만_고른다():
    """아무 CSV 나 집으면 엉뚱한 표를 읽고 '부품을 못 찾았습니다' 가 나온다."""
    got = [c.path for c in repo.bom_candidates(PLATFORMIO_REPO + MESSY_REPO)]
    assert got == ["pcb/bom_v3.csv"]
    assert "data/output.csv" not in got


# ------------------------------------------------------------ 근거

def test_모든_후보가_왜_골랐는지_말한다():
    """근거가 없으면 사용자는 우리 추천을 검증할 방법이 없다."""
    scan = repo.scan(KICAD_REPO + PLATFORMIO_REPO)
    for group in scan.to_dict().values():
        for item in group["candidates"]:
            assert item["reason"].strip()


# ------------------------------------------------------------ 워크플로

def test_만든_워크플로가_유효한_yaml_이다():
    import yaml
    got = yaml.safe_load(repo.workflow_yaml("hardware/board.net.xml", "firmware/main", "hardware/bom.csv"))
    step = got["jobs"]["prefab"]["steps"][1]
    assert step["with"]["netlist"] == "hardware/board.net.xml"
    assert step["with"]["fail-on"] == "critical"


def test_선택_입력은_없으면_안_적는다():
    """빈 값을 적으면 액션이 '펌웨어를 못 찾았습니다' 로 죽는다."""
    got = repo.workflow_yaml("board.d356")
    assert "firmware:" not in got
    assert "bom:" not in got


def test_경로에_특수문자가_있어도_안_깨진다():
    """남의 저장소 경로는 우리가 정하지 않는다. 콜론 하나로 YAML 이 달라진다."""
    import yaml
    got = yaml.safe_load(repo.workflow_yaml("hw: 보드/board.net.xml"))
    assert got["jobs"]["prefab"]["steps"][1]["with"]["netlist"] == "hw: 보드/board.net.xml"


def test_액션_주소가_공개_경로다():
    """남이 복사해 쓰는 주소다. 로컬 경로(`./`)를 적으면 남의 저장소에서 안 돈다."""
    assert not repo.ACTION_REF.startswith("./")
    assert repo.ACTION_REF.startswith("PNU-2026-AI-Hackathon/")


def test_우리가_만든_워크플로를_액션이_실제로_받는다():
    """**만들어 준 파일이 액션과 안 맞으면 남의 저장소에서만 깨진다.**

    우리 자가 시험은 우리가 손으로 쓴 워크플로를 돌리므로 이 어긋남을 못 잡는다.
    그래서 여기서 생성물과 액션 정의를 직접 맞춰 본다.
    """
    import pathlib

    import yaml

    action_file = (
        pathlib.Path(__file__).parents[3] / ".github/actions/prefab-check/action.yml"
    )
    assert action_file.exists(), action_file
    action = yaml.safe_load(action_file.read_text())

    made = yaml.safe_load(repo.workflow_yaml("a.d356", "fw", "b.csv"))
    given = made["jobs"]["prefab"]["steps"][1]["with"]

    # ① 우리가 넘기는 입력이 액션에 **다 있는가**
    unknown = set(given) - set(action["inputs"])
    assert not unknown, f"액션이 모르는 입력: {unknown}"

    # ② 액션이 **반드시 받아야 하는 것**을 우리가 다 넘기는가
    required = {k for k, v in action["inputs"].items() if v.get("required")}
    assert required <= set(given), f"안 넘긴 필수 입력: {required - set(given)}"

    # ③ 시크릿 이름이 같은가 — 다르면 401 이 나고 원인 찾기가 어렵다
    assert "secrets.PREFAB_API_KEY" in repo.workflow_yaml("a.d356")


def test_워크플로가_PR_코멘트_권한을_준다():
    """권한이 없으면 코멘트에서 403 이 난다.

    GitHub 의 기본 토큰은 읽기 전용이라, 이 블록을 빼면 요약은 나오지만
    PR 코멘트가 조용히 실패한다. 실제로 시연 저장소에서 그렇게 났다.
    """
    y = repo.workflow_yaml("hardware/board.net.xml", firmware="firmware")
    assert "permissions:" in y
    assert "pull-requests: write" in y
    assert "contents: read" in y
