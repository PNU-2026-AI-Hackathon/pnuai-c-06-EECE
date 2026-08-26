"""저장소를 훑어 「무엇이 어디 있는지」 찾는다.

## 왜 이게 필요한가

CI 를 붙이려면 지금 네 단계를 밟아야 한다 — 키 만들고, 시크릿 넣고, YAML 쓰고,
**경로를 맞추고.** 넷 중 마지막에서 제일 많이 틀린다. 남의 저장소마다 회로도가
`hardware/` 에 있기도 하고 `pcb/` 나 `electronics/` 에 있기도 하다.

우리가 저장소를 한 번 읽으면 그 네 번째를 대신할 수 있다.

## 틀린 경로를 자신 있게 적어 주는 것이 제일 나쁘다

경로를 틀리게 넣으면 액션이 "넷리스트를 못 찾았습니다" 로 죽는다. 사용자는
**우리 도구가 고장 났다고 읽는다** — 자기가 고를 기회조차 없었기 때문이다.

그래서 이 모듈은 **고르지 않는다. 후보를 근거와 함께 늘어놓는다.**
확신이 있으면 하나를 기본으로 표시하고, 없으면 없다고 말한다 (헌법 2-2·2-3).

## 확장자만으로는 못 가른다

`.txt` 와 `.xml` 은 세상에서 제일 흔한 확장자다. `README.txt` 를 넷리스트라고
집으면 그게 곧 오탐이다. 그래서 두 단계로 본다 —

    1. 이름과 경로로 **후보를 좁힌다** (이 파일, 순수 함수)
    2. 후보의 앞부분만 실제로 읽어 **형식을 확인한다** (`prefab.netlist.detect`)

2단계를 후보 몇 개에만 돌리므로 저장소 전체를 내려받지 않는다.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass

#: 넷리스트일 수 있는 확장자.
#:
#: **확신의 등급이 다르다.** `.d356` 은 이 형식 전용이라 이름만으로 거의 확실하고,
#: `.xml` 은 세상 모든 설정 파일이 쓰는 확장자라 내용을 봐야 안다.
NETLIST_SURE = (".d356", ".ipc")
NETLIST_MAYBE = (".xml", ".net", ".txt")

#: 펌웨어 소스. `check.py` 가 올리는 것과 **같은 목록이다** —
#: 여기서 더 담아 봐야 서버가 안 본다 (헌법 10절).
FIRMWARE_SUFFIXES = (".ino", ".cpp", ".c", ".h", ".hpp")

#: 이 폴더 안은 남의 코드이거나 빌드 산출물이다. 후보에서 뺀다.
SKIP_DIRS = (
    "node_modules", ".git", "build", "dist", ".pio", "lib", "libraries",
    "managed_components", "vendor", "third_party", ".venv", "__pycache__",
)

#: 회로도가 사는 흔한 폴더 이름. **가산점이지 조건이 아니다** —
#: 저장소 뿌리에 그냥 두는 사람도 많다.
HARDWARE_HINTS = ("hardware", "hw", "pcb", "kicad", "electronics", "board", "schematic")

#: 펌웨어가 사는 흔한 폴더 이름.
FIRMWARE_HINTS = ("firmware", "fw", "src", "arduino", "sketch", "app")

#: BOM 으로 보이는 이름.
_BOM_NAME = re.compile(r"(bom|bill.?of.?materials|부품)", re.I)


@dataclass(frozen=True)
class Candidate:
    """후보 하나. **왜 골랐는지 같이 들고 다닌다.**

    근거가 없으면 사용자는 우리 추천을 검증할 방법이 없고, 그러면 틀렸을 때
    자기가 고를 기회 없이 당한다.
    """

    path: str
    #: 0.0 ~ 1.0. **확률이 아니다** — 후보끼리 줄 세우는 값이다.
    score: float
    #: 사람이 읽을 근거. 화면에 그대로 나간다.
    reason: str

    def to_dict(self) -> dict:
        return {"path": self.path, "score": round(self.score, 2), "reason": self.reason}


def _skipped(path: str) -> bool:
    parts = path.split("/")[:-1]
    return any(p in SKIP_DIRS or p.startswith(".") for p in parts)


def _hint_bonus(path: str, hints: tuple[str, ...]) -> tuple[float, str | None]:
    """경로에 익숙한 폴더 이름이 있으면 가산점."""
    lowered = [p.lower() for p in path.split("/")[:-1]]
    for hint in hints:
        if hint in lowered:
            return 0.2, f"{hint}/ 아래에 있습니다"
    return 0.0, None


def netlist_candidates(paths: list[str]) -> list[Candidate]:
    """넷리스트일 수 있는 파일. **점수 높은 순.**

    `.txt` 를 후보에 넣되 점수를 낮게 준다. IPC-D-356 을 `.txt` 로 내보내는
    도구가 실제로 있어서 빼면 그 사람들이 통째로 막힌다. 대신 이름이나 경로에
    다른 단서가 없으면 뒤로 밀린다.
    """
    found: list[Candidate] = []
    for path in paths:
        if _skipped(path):
            continue
        name = posixpath.basename(path).lower()
        bonus, hint = _hint_bonus(path, HARDWARE_HINTS)

        if name.endswith(NETLIST_SURE):
            score, why = 0.9, "IPC-D-356 전용 확장자입니다"
        elif name.endswith(".net.xml") or name.endswith(".net"):
            score, why = 0.8, "회로도 넷리스트로 보이는 이름입니다"
        elif name.endswith(".xml"):
            # **거의 다 아니다.** 내용을 봐야 알므로 후보로만 남긴다.
            score, why = 0.25, "확장자만으로는 모릅니다 — 내용을 확인해야 합니다"
        elif name.endswith(".txt"):
            score, why = 0.15, "일부 도구가 IPC-D-356 을 .txt 로 내보냅니다"
        else:
            continue

        if "netlist" in name or "netlist" in path.lower():
            score, why = min(1.0, score + 0.25), "이름에 netlist 가 들어 있습니다"
        if hint:
            score = min(1.0, score + bonus)
            why = f"{why} · {hint}"
        found.append(Candidate(path, score, why))

    return sorted(found, key=lambda c: (-c.score, c.path))


def firmware_candidates(paths: list[str]) -> list[Candidate]:
    """펌웨어 **폴더.** 파일이 아니라 폴더를 고른다 (액션이 폴더를 받는다).

    소스 파일이 든 폴더를 모아 놓고, `.ino` 가 있으면 크게 올린다 —
    아두이노 스케치는 회로도와 짝인 것이 거의 확실하다.
    """
    tally: dict[str, dict] = {}
    for path in paths:
        if _skipped(path):
            continue
        name = posixpath.basename(path).lower()
        if not name.endswith(FIRMWARE_SUFFIXES):
            continue
        folder = posixpath.dirname(path) or "."
        slot = tally.setdefault(folder, {"n": 0, "ino": False})
        slot["n"] += 1
        slot["ino"] = slot["ino"] or name.endswith(".ino")

    found = []
    for folder, slot in tally.items():
        score = 0.45 + min(0.25, slot["n"] * 0.05)
        why = f"소스 {slot['n']}개가 있습니다"
        if slot["ino"]:
            score, why = score + 0.3, f"아두이노 스케치(.ino)가 있습니다 · {why}"
        bonus, hint = _hint_bonus(folder + "/x", FIRMWARE_HINTS)
        if hint:
            score, why = score + bonus, f"{why} · {hint}"
        found.append(Candidate(folder, min(1.0, score), why))

    return sorted(found, key=lambda c: (-c.score, c.path))


def bom_candidates(paths: list[str]) -> list[Candidate]:
    """부품 목록 CSV. **이름에 bom 이 없으면 안 고른다.**

    저장소의 아무 CSV 나 부품 목록이라고 집으면, 엉뚱한 표를 읽고 "부품을 못
    찾았습니다" 가 나온다. 그건 안 넣느니만 못하다 — BOM 은 선택 입력이라
    없으면 없는 대로 검사가 돈다.
    """
    found = []
    for path in paths:
        if _skipped(path) or not path.lower().endswith(".csv"):
            continue
        name = posixpath.basename(path)
        if not _BOM_NAME.search(name):
            continue
        score, why = 0.8, "이름이 부품 목록으로 보입니다"
        bonus, hint = _hint_bonus(path, HARDWARE_HINTS)
        if hint:
            score, why = min(1.0, score + bonus), f"{why} · {hint}"
        found.append(Candidate(path, score, why))
    return sorted(found, key=lambda c: (-c.score, c.path))


#: 이 아래로는 「우리가 골라도 되는」 확신이 아니다.
#:
#: 넘으면 화면이 그 후보를 미리 채워 두고, 못 넘으면 **비워 둔 채 고르라고 한다.**
#: 틀린 값을 채워 두는 것이 빈칸보다 나쁘다 — 사용자가 검토를 건너뛰기 때문이다.
CONFIDENT = 0.7


@dataclass(frozen=True)
class Scan:
    """저장소를 훑은 결과."""

    netlist: list[Candidate]
    firmware: list[Candidate]
    bom: list[Candidate]

    @staticmethod
    def _pick(items: list[Candidate]) -> str | None:
        """확신이 있을 때만 고른다. **애매하면 `None`.**"""
        if not items or items[0].score < CONFIDENT:
            return None
        # 1등과 2등이 비슷하면 우리가 고를 일이 아니다 — 사람이 안다.
        if len(items) > 1 and items[1].score >= items[0].score - 0.1:
            return None
        return items[0].path

    def to_dict(self) -> dict:
        return {
            "netlist": {
                "picked": self._pick(self.netlist),
                "candidates": [c.to_dict() for c in self.netlist[:8]],
            },
            "firmware": {
                "picked": self._pick(self.firmware),
                "candidates": [c.to_dict() for c in self.firmware[:8]],
            },
            "bom": {
                "picked": self._pick(self.bom),
                "candidates": [c.to_dict() for c in self.bom[:8]],
            },
        }


def scan(paths: list[str]) -> Scan:
    """**순수 함수다.** 저장소 파일 목록만 받는다 — 네트워크를 모른다."""
    return Scan(
        netlist=netlist_candidates(paths),
        firmware=firmware_candidates(paths),
        bom=bom_candidates(paths),
    )


# ---------------------------------------------------- 워크플로 파일 만들기

#: 저장소에 넣을 파일 자리. **`.github/workflows/` 여야 GitHub 이 실행한다.**
WORKFLOW_PATH = ".github/workflows/prefab.yml"

#: 우리 액션을 가리키는 주소. 태그가 아니라 `@main` 인 이유는,
#: 대회 기간에 액션을 고치면 남의 저장소에도 바로 반영돼야 하기 때문이다.
#: **정식 배포하면 태그로 바꾼다** — 남의 CI 가 우리 커밋마다 바뀌면 안 된다.
ACTION_REF = "PNU-2026-AI-Hackathon/pnuai-c-06-EECE/.github/actions/prefab-check@main"


def _yaml_value(raw: str) -> str:
    """YAML 에 넣을 값. **경로에 특수문자가 있으면 따옴표로 감싼다.**

    남의 저장소 경로는 우리가 정하지 않는다. `hw: board.net.xml` 처럼 콜론이
    들어가면 YAML 이 다른 뜻으로 읽고, 액션이 엉뚱한 오류로 죽는다.
    """
    if raw and not re.search(r"[:#\[\]{}&*!|>'\"%@`,\s]", raw):
        return raw
    return "'" + raw.replace("'", "''") + "'"


def workflow_yaml(netlist: str, firmware: str | None = None, bom: str | None = None) -> str:
    """PR 마다 검사를 돌리는 워크플로. **순수 함수다.**

    `fail-on: critical` 로 둔다 — 경고까지 막으면 첫 주에 꺼진다 (헌법 2-3).
    """
    lines = [
        "# Prefab — 회로도와 펌웨어가 어긋난 곳을 보드 발주 전에 찾습니다.",
        "#",
        "# 이 파일은 prefab-web.onrender.com 이 만들어 준 것입니다.",
        "# 경로가 틀렸으면 아래 값을 고치세요.",
        "",
        "name: 회로도와 코드 대조",
        "",
        "on:",
        "  pull_request:",
        "",
        "jobs:",
        "  prefab:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - uses: actions/checkout@v4",
        "",
        f"      - uses: {ACTION_REF}",
        "        with:",
        "          api-key: ${{ secrets.PREFAB_API_KEY }}",
        f"          netlist: {_yaml_value(netlist)}",
    ]
    if firmware:
        lines.append(f"          firmware: {_yaml_value(firmware)}")
    if bom:
        lines.append(f"          bom: {_yaml_value(bom)}")
    lines += [
        "          # 치명 발견이 있으면 빨간불이 켜집니다.",
        "          # 경고까지 막으려면 warning 으로 바꾸세요.",
        "          fail-on: critical",
        "",
    ]
    return "\n".join(lines)
