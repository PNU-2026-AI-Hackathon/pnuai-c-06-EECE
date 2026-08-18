"""한국어 조사 처리.

발견 문구는 사용자에게 **그대로** 노출된다. `R1는`, `K1와` 처럼 조사가 어긋나면
읽는 사람이 도구를 대충 만든 것으로 본다. 근거가 맞아도 신뢰가 깎인다.

부품 기호는 대부분 `U1` · `K1` 처럼 숫자로 끝난다. 숫자를 한국어로 읽었을 때
받침이 있는지로 갈린다 — 1(일) · 3(삼) · 6(육) · 7(칠) · 8(팔) · 0(영)은 받침이 있고,
2(이) · 4(사) · 5(오) · 9(구)는 없다.
"""

from __future__ import annotations

#: 한국어로 읽었을 때 받침으로 끝나는 숫자
_DIGITS_WITH_FINAL = frozenset("013678")

#: 알파벳 이름이 받침으로 끝나는 글자 — 엘 · 엠 · 엔 · 알
_LETTERS_WITH_FINAL = frozenset("LMNR")

_HANGUL_BASE = 0xAC00
_HANGUL_LAST = 0xD7A3
_JONGSEONG_COUNT = 28


def has_final(word: str) -> bool:
    """마지막 글자가 받침으로 끝나는가. 판단할 수 없으면 False."""
    if not word:
        return False
    ch = word.strip()[-1:]
    if not ch:
        return False
    if ch.isdigit():
        return ch in _DIGITS_WITH_FINAL
    if _HANGUL_BASE <= ord(ch) <= _HANGUL_LAST:
        return (ord(ch) - _HANGUL_BASE) % _JONGSEONG_COUNT != 0
    if ch.isalpha():
        return ch.upper() in _LETTERS_WITH_FINAL
    return False


def josa(word: str, with_final: str, without_final: str) -> str:
    """`josa("U1", "은", "는")` → `"U1은"`."""
    return word + (with_final if has_final(word) else without_final)


def eun(word: str) -> str:
    return josa(word, "은", "는")


def i_ga(word: str) -> str:
    return josa(word, "이", "가")


def gwa(word: str) -> str:
    return josa(word, "과", "와")


def eul(word: str) -> str:
    return josa(word, "을", "를")


def euro(word: str) -> str:
    """으로 / 로"""
    return josa(word, "으로", "로")
