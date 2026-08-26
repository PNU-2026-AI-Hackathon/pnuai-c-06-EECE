"""드리프트 워크플로 **한 쌍**이 어긋나지 않게 잡는다.

## 왜 이 테스트가 있는가

`drift.yml` 은 회로도가 바뀐 PR 에서만 돈다. 그런데 브랜치 보호가 그 검사를
**필수로 요구**하므로, 안 도는 PR 은 보고를 영영 못 받고 초록인 채로 막힌다.
2026-08-27 에 PR #95 가 실제로 그렇게 막혔다.

그래서 반대 조건으로 도는 `drift-skip.yml` 을 뒀다. **둘 중 하나는 반드시 돈다.**

## 무엇이 깨지면 다시 막히는가

    잡 이름이 달라지면    보호가 검사를 못 찾는다
    경로 목록이 갈리면    둘 다 안 도는 PR 이 생긴다

둘 다 사람이 한쪽만 고치면서 생긴다. **YAML 두 개를 손으로 맞추는 일이라 반드시
어긋난다** — 그래서 코드가 본다.
"""

from __future__ import annotations

import pathlib
import re

import pytest

WF = pathlib.Path(__file__).parents[3] / ".github/workflows"
DRIFT = WF / "drift.yml"
SKIP = WF / "drift-skip.yml"


def _job_name(text: str) -> str:
    m = re.search(r"^    name:\s*(.+)$", text, re.M)
    assert m, "잡 이름을 못 찾았습니다"
    return m.group(1).strip().strip('"')


def _paths(text: str, key: str) -> set[str]:
    body = text.split(f"{key}:", 1)[1].split("jobs:", 1)[0]
    return {p.strip().strip('"') for p in re.findall(r'^\s+- (.+)$', body, re.M)}


def test_둘_다_있다():
    assert DRIFT.exists(), DRIFT
    assert SKIP.exists(), "짝이 없으면 안 도는 PR 이 영영 막힙니다"


def test_잡_이름이_같다():
    """**보호는 이름으로 찾는다.** 다르면 짝이 있어도 못 찾는다."""
    assert _job_name(DRIFT.read_text()) == _job_name(SKIP.read_text())


def test_경로가_정확히_반대다():
    """한쪽만 고치면 **둘 다 안 도는 PR** 이 생기고, 그 PR 은 영영 막힌다."""
    runs = _paths(DRIFT.read_text(), "paths")
    skips = _paths(SKIP.read_text(), "paths-ignore")
    assert runs == skips, (
        f"경로가 어긋났습니다.\n  drift 만: {runs - skips}\n  skip 만: {skips - runs}"
    )


def test_건너뛰기는_아무것도_검사하지_않는다():
    """**초록만 보고한다.** 여기서 뭔가 검사하면 그건 이름을 속이는 것이다."""
    text = SKIP.read_text()
    for forbidden in ("prefab", "python -m", "pytest", "--diff"):
        assert forbidden not in text.split("jobs:")[1], f"건너뛰기 잡이 {forbidden} 를 부릅니다"


@pytest.mark.parametrize("path", ["apps/api/board/board.net.xml", "apps/api/src/prefab/engine.py"])
def test_보드가_바뀌면_진짜_대조가_돈다(path):
    """이 경로들은 **건너뛰기가 아니라 진짜 검사**를 타야 한다."""
    runs = _paths(DRIFT.read_text(), "paths")
    assert any(path.startswith(p.rstrip("*").rstrip("/")) for p in runs), path
