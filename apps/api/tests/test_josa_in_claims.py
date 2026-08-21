"""사용자에게 나가는 문구에 조사가 손으로 박혀 있지 않은지.

**헌법 11절이 `K1와` 를 하지 말라는 예시로 들고 있는데, 실제로 그렇게 나가고 있었다.**

    5V 로 도는 K1 와 3.3V 로 도는 U1 가 같은 네트에 있습니다.
                 ^^^^                ^^^^

`K1` 은 "케이일" 이라 받침이 있다 — `K1과` · `U1이` 가 맞다. 판정이 맞아도 이런 문구가
나가면 읽는 사람이 도구를 대충 만든 것으로 본다. 그래서 문구 버그를 판정 버그와
같은 급으로 취급한다.

여기서는 **소스에 f-string 보간 바로 뒤에 조사가 붙어 있는지**를 본다. 렌더된 결과를
훑는 방식은 그 문구가 실제로 나온 케이스에서만 잡히는데, 규칙 대부분은 우리 픽스처에서
안 뜬다. 소스를 보면 안 뜬 규칙까지 같이 지킨다.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RULES_DIR = Path(__file__).parent.parent / "src" / "prefab" / "rules"

#: 보간 바로 뒤에 오면 안 되는 조사들. 앞말의 받침에 따라 갈리는 것만 본다.
#: (`의` · `에` · `로` 처럼 안 갈리는 것은 박아도 된다.)
PAIRED_JOSA = ("은", "는", "이", "가", "을", "를", "와", "과")

#: `{something} 은` 또는 `{something}은` — 보간 뒤 공백 0~1칸 다음에 조사, 그리고 어절 끝.
PATTERN = re.compile(
    r"\}\s?(" + "|".join(PAIRED_JOSA) + r")(?=[\s.,)\"']|$)"
)

#: 조사가 아니라 다른 뜻으로 쓰인 자리. **늘리기 전에 정말 조사가 아닌지 확인할 것.**
#:
#: 여기 넣는 순간 그 줄은 검사에서 빠진다. 실제 조사 버그를 여기 넣어 통과시키면
#: 검사기가 있는 것이 없는 것보다 나쁘다 — 지켜지고 있다고 착각하게 되니까.
ALLOW = (
    "}이다",       # 서술격 조사 — 앞말의 받침과 무관하게 문장을 끝낸다
    "}입니다",
    "} 이 네트",   # 지시사 "이" — `{need} 이 네트의 저항은` 은 "this net" 이지 조사가 아니다
)


def _rule_files() -> list[Path]:
    return sorted(p for p in RULES_DIR.glob("*.py") if not p.name.startswith("_"))


@pytest.mark.parametrize("path", _rule_files(), ids=lambda p: p.stem)
def test_보간_뒤에_조사를_박지_않는다(path: Path):
    offenders: list[str] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue                       # 주석은 사용자에게 안 나간다
        if any(a in line for a in ALLOW):
            continue
        if PATTERN.search(line):
            offenders.append(f"{path.name}:{lineno}  {stripped[:90]}")

    assert not offenders, (
        "보간 뒤에 조사가 박혀 있습니다. `text.py` 의 eun · i_ga · eul · gwa 를 쓰세요 —\n  "
        + "\n  ".join(offenders)
    )


def test_이_검사가_실제로_잡는다():
    """검사기가 아무것도 안 잡는 상태로 통과하면 의미가 없다."""
    assert PATTERN.search('f"{hi} 와 {lo} 가 같은 네트"')
    assert PATTERN.search('f"코드가 {where}를 사용합니다"')
    # 갈리지 않는 조사는 건드리지 않는다
    assert not PATTERN.search('f"{where} 에서 {net} 로"')
    assert not PATTERN.search('f"{ref}의 전원"')
