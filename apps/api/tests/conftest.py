"""테스트 공용 — **검사를 만들려면 로그인해야 한다** (8/24, CLAUDE.md 4절).

그 결정이 들어오면서 HTTP 테스트 19개가 한꺼번에 401 을 받았다. 전부 "검사를
만든다"를 전제로 쓴 것들이다. 각 파일에서 따로 가입 절차를 흉내 내면 그 절차가
바뀔 때마다 네 곳을 고치게 되므로 여기 하나만 둔다.

**결과를 *보는* 것은 여전히 로그인이 필요 없다.** 그 선을 지키는 테스트는
로그인하지 않은 클라이언트를 그대로 쓴다.
"""

from __future__ import annotations

import pytest

#: 가입에 쓰는 비밀번호. 길이만 보므로(10자 이상) 외우기 쉬운 문장이면 된다.
TEST_PASSWORD = "correct horse battery staple"


def sign_in(client, email: str = "tester@example.com") -> None:
    """이 클라이언트를 로그인 상태로 만든다.

    `TestClient` 는 쿠키를 들고 다니므로 가입 한 번이면 이후 요청이 전부 그 계정이다.
    이미 있는 계정이면 로그인으로 넘어간다 — 같은 테스트 안에서 두 번 불러도 된다.
    """
    res = client.post(
        "/api/v1/auth/signup", json={"email": email, "password": TEST_PASSWORD}
    )
    if res.status_code == 201:
        return
    res = client.post(
        "/api/v1/auth/login", json={"email": email, "password": TEST_PASSWORD}
    )
    assert res.status_code == 200, res.text


@pytest.fixture()
def signed_in(client):
    """로그인된 클라이언트. **검사를 만드는 테스트는 전부 이걸 쓴다.**"""
    sign_in(client)
    return client
