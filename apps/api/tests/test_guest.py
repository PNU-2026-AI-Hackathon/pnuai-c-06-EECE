"""게스트 체험 표.

**이건 요금 방어선이 아니다.** 쿠키를 지우면 다시 한 번 쓸 수 있고 그게 의도다.
여기서 지키는 것은 두 가지뿐이다 —

    1. 남이 만든 표를 안 받는다 (아무나 무제한이 되면 안 된다)
    2. 못 읽는 표를 「많이 썼다」로 치지 않는다 (쿠키가 깨진 사람이 영영 막히면 안 된다)
"""

from __future__ import annotations

import time

import pytest

from web import guest


def test_방금_만든_표를_읽는다():
    assert guest.used_count(guest.issue(1)) == 1


def test_안_쓴_사람은_한_번_남는다():
    assert guest.remaining(None) == guest.FREE_CHECKS


def test_한_번_쓰면_안_남는다():
    assert guest.remaining(guest.issue(1)) == 0


def test_남이_만든_표는_안_받는다():
    """서명이 없으면 아무나 «0번 썼음» 표를 찍어서 무제한이 된다."""
    assert guest.used_count("1.99999999999.aaaaaaaa") == 0
    assert guest.used_count("0.99999999999.deadbeef") == 0


@pytest.mark.parametrize("raw", [None, "", "쓰레기", "1.2", "a.b.c", "1.abc.def"])
def test_못_읽는_표는_안_쓴_것으로_본다(raw):
    """**관대한 쪽이 맞다.** 여기서 틀렸을 때의 손해는 한 번 더 써 보는 것뿐이고,
    반대로 틀리면 쿠키가 깨진 사람이 영영 못 쓴다."""
    assert guest.used_count(raw) == 0


def test_지난_표는_안_쓴_것으로_본다():
    old = guest.issue(1, now=int(time.time()) - guest.TTL_SECONDS - 10)
    assert guest.used_count(old) == 0


def test_표에_사용자를_안_담는다():
    """게스트는 계정이 없다. 표에 신원이 들어가면 그때부터 개인정보가 된다."""
    ticket = guest.issue(1)
    assert "@" not in ticket
    assert ticket.count(".") == 2
