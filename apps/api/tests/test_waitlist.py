"""출시 알림 대기 명단.

**결제를 만들기 전에 살 사람이 있는지 재는 자리다.** 요금표가 「준비 중」이라고만
적혀 있는 동안은 방문자가 반응할 대상이 없어서, 비싼지 싼지조차 알 수 없다.
그래서 이 표의 정확성이 곧 가격 결정의 근거가 된다 — 중복이 섞이면 그 숫자가 거짓말이다.
"""

from __future__ import annotations

import sqlite3

import pytest

from web import waitlist


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    waitlist.init(c)
    yield c
    c.close()


def test_대소문자와_공백이_달라도_같은_사람이다(conn):
    """`Me@Example.COM` 과 `me@example.com` 을 두 명으로 세면 수요를 부풀려 읽는다."""
    waitlist.join(conn, "  Me@Example.COM  ", "pro")
    waitlist.join(conn, "me@example.com", "pro")
    assert waitlist.count(conn, "pro") == 1


def test_같은_사람이_다른_요금제를_기다릴_수_있다(conn):
    waitlist.join(conn, "me@example.com", "pro")
    waitlist.join(conn, "me@example.com", "team")
    assert waitlist.count(conn) == 2
    assert waitlist.count(conn, "pro") == 1
    assert waitlist.count(conn, "team") == 1


def test_중복_등록은_조용히_성공한다(conn):
    """「이미 등록하셨습니다」는 사용자에게 쓸모가 없다.

    그리고 그 문구는 **이 주소가 명단에 있다는 사실을 아무에게나 알려주는 셈**이다.
    """
    waitlist.join(conn, "me@example.com", "pro")
    waitlist.join(conn, "me@example.com", "pro")  # 예외가 나면 안 된다
    assert waitlist.count(conn) == 1


@pytest.mark.parametrize(
    "email, code",
    [
        ("", "EMAIL_REQUIRED"),
        ("   ", "EMAIL_REQUIRED"),
        ("아님", "EMAIL_INVALID"),
        ("a@b", "EMAIL_INVALID"),          # 점이 없다
        ("a b@c.com", "EMAIL_INVALID"),    # 공백이 들어 있다
        ("x" * 250 + "@example.com", "EMAIL_TOO_LONG"),
    ],
)
def test_주소가_아닌_값은_이유와_함께_거절한다(conn, email, code):
    with pytest.raises(waitlist.WaitlistError) as got:
        waitlist.join(conn, email, "pro")
    assert got.value.code == code
    assert got.value.message  # 사용자에게 그대로 보여줄 문구가 있다


def test_모르는_요금제는_거절한다(conn):
    """프론트가 오타를 내면 조용히 저장되고, 나중에 집계가 틀린다."""
    with pytest.raises(waitlist.WaitlistError) as got:
        waitlist.join(conn, "me@example.com", "gold")
    assert got.value.code == "PLAN_UNKNOWN"
    assert waitlist.count(conn) == 0


def test_받는_요금제는_두_개뿐이다():
    """화면과 서버가 같은 목록을 봐야 한다. 늘리려면 양쪽을 같이 고친다."""
    assert waitlist.PLANS == ("pro", "team")
