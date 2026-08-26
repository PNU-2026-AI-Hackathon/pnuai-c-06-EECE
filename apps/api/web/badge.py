"""상태 배지 — **남의 README 에 붙는 우리 얼굴.**

## 왜 SVG 를 우리가 그리는가

shields.io 를 쓰면 한 줄이면 된다. 안 쓰는 이유는 **남의 저장소가 우리를
읽으려고 제3자를 거치게 되기 때문**이다. 그 서비스가 죽으면 남의 README 가
깨지고, 그쪽 로그에는 우리 사용자의 저장소 이름이 남는다.

의존성도 없다 — 문자열 하나를 만들어 돌려주면 된다.

## 캐시를 짧게 두는 이유

GitHub 은 README 이미지를 자기 프록시(camo)로 가져가 캐시한다. 길게 두면
치명이 고쳐졌는데 배지가 며칠째 빨갛게 남는다. **틀린 배지는 없느니만 못하다.**

## 글자 폭을 왜 재는가

SVG 에는 자동 줄바꿈이 없다. 폭을 안 재면 긴 글자가 배지 밖으로 삐져나온다.
정확한 폰트 메트릭 대신 **문자 종류별 평균 폭**을 쓴다 — 한 글자 어긋나도
배지는 안 깨지고, 폰트 파일을 싣지 않아도 된다.
"""

from __future__ import annotations

#: 색. `tailwind.config.js` 의 역할 색과 같은 값을 쓴다 —
#: 배지는 우리 화면 밖에 있지만 **같은 제품**이다.
COLORS = {
    "crit": "#D6293E",
    "warn": "#B45309",
    "ok": "#087A57",
    "mute": "#8B95A1",
}

#: 왼쪽 라벨. 바꾸지 않는다 — 남의 README 에 이미 박혀 있다.
LABEL = "prefab"

_H = 20
_PAD = 6


def _width(text: str) -> int:
    """글자 폭 어림. **한글은 라틴 문자의 약 두 배다.**"""
    w = 0.0
    for ch in text:
        if ord(ch) > 0x2E80:      # 한글·한자·가나
            w += 12.0
        elif ch in "iljI.,:;'|":  # 좁은 글자
            w += 3.4
        elif ch.isdigit():
            w += 6.2
        elif ch.isupper():
            w += 8.0
        else:
            w += 6.4
    return int(w + 0.5)


def summarize(critical: int, warning: int) -> tuple[str, str]:
    """`(오른쪽 글자, 색)`. **0건을 「이상 없음」이라고 말하지 않는다.**

    이 도구가 못 돌린 규칙이 있을 수 있고, 배지에는 그걸 적을 자리가 없다.
    그래서 「통과」가 아니라 「발견 없음」이다 (헌법 2-4).
    """
    if critical:
        return (f"치명 {critical}건", COLORS["crit"])
    if warning:
        return (f"경고 {warning}건", COLORS["warn"])
    return ("발견 없음", COLORS["ok"])


def unknown() -> tuple[str, str]:
    """검사 결과를 못 찾은 경우. **초록으로 칠하지 않는다.**"""
    return ("검사 없음", COLORS["mute"])


def render(right: str, color: str) -> str:
    """배지 SVG. **순수 함수다.**"""
    lw = _width(LABEL) + _PAD * 2
    rw = _width(right) + _PAD * 2
    total = lw + rw

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{_H}" '
        f'role="img" aria-label="{LABEL}: {right}">'
        f"<title>{LABEL}: {right}</title>"
        f'<rect width="{total}" height="{_H}" rx="3" fill="#191F28"/>'
        f'<path fill="{color}" d="M{lw} 0h{rw - 3}a3 3 0 0 1 3 3v14a3 3 0 0 1-3 3H{lw}z"/>'
        f'<g fill="#fff" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,'
        f'Apple SD Gothic Neo,sans-serif" font-size="11">'
        f'<text x="{lw / 2}" y="14" text-anchor="middle" opacity=".9">{LABEL}</text>'
        f'<text x="{lw + rw / 2}" y="14" text-anchor="middle" font-weight="600">{right}</text>'
        f"</g></svg>"
    )
