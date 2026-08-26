"""게스트 체험 — **가입 벽을 결과 앞에서 뒤로 옮긴다.**

## 무엇을 바꾸는가

8/24 에 「검사는 로그인해야 만들 수 있다」로 정했다(`CLAUDE.md` 4절). 그 결정은
그대로다 — **바꾸는 것은 벽의 위치**다.

    전:  가치를 보기 **전**에 가입을 요구한다
    후:  한 번 써 본 **뒤**에 가입을 요구한다

처음 온 사람은 넷리스트가 뭔지도 모르고, 이 도구가 무엇을 내놓는지도 못 본
상태에서 계정을 내놓으라는 요구를 받았다. 경쟁 서비스를 직접 써 보니 그 벽이
아예 없는 곳도 있었다.

## 왜 「한 번」인가

**비용이 아니라 신원 때문이다.** 판정은 순수한 코드라 검사 한 번에 드는 비용이
사실상 0이다. 그래서 횟수를 아끼려는 게 아니다 — 계속 쓸 사람은 결과가 남아야
하고, 결과가 남으려면 계정이 있어야 한다.

한 번이면 **무엇을 내놓는 도구인지 보기에 충분하다.** 두 번째부터는 이미 안다.

## 어떻게 세는가

브라우저에 짧게 사는 쿠키를 심고, 서명해서 위조를 막는다. **DB 에 안 넣는다** —
게스트는 계정이 없어서 넣을 자리가 없고, 우리 DB 는 재배포마다 비워진다.

**이건 요금 방어선이 아니다.** 쿠키를 지우면 다시 한 번 쓸 수 있고, 그건 의도한
것이다. 진짜 방어선은 요청 제한(`ratelimit.py`)이고 그건 그대로 돈다.
"""

from __future__ import annotations

import hmac
import os
import secrets
import time
from hashlib import sha256

#: 게스트가 로그인 없이 만들 수 있는 검사 수.
FREE_CHECKS = 1

#: 표를 들고 다니는 쿠키. httpOnly 라 화면 코드가 못 건드린다.
COOKIE = "prefab_guest"

#: 쿠키 수명. 하루면 「보고 → 마음 정하고 → 가입」에 넉넉하다.
TTL_SECONDS = 24 * 60 * 60

#: 서명 열쇠. 세션 비밀과 같은 자리에서 온다.
#:
#: **없으면 기동 때 한 번 만든다.** 그러면 재시작마다 옛 표가 무효가 되는데,
#: 게스트 표는 잃어도 손해가 「한 번 더 써 볼 수 있다」뿐이라 괜찮다.
_SECRET = os.getenv("GUEST_SECRET") or secrets.token_hex(32)


def _sign(payload: str) -> str:
    return hmac.new(_SECRET.encode(), payload.encode(), sha256).hexdigest()[:32]


def issue(used: int, now: int | None = None) -> str:
    """`쓴횟수.만료.서명`. 서버에 아무것도 안 남긴다."""
    expires = (now if now is not None else int(time.time())) + TTL_SECONDS
    payload = f"{used}.{expires}"
    return f"{payload}.{_sign(payload)}"


def used_count(raw: str | None, now: int | None = None) -> int:
    """이 브라우저가 몇 번 썼는가. **읽을 수 없으면 0으로 본다.**

    위조나 만료를 「많이 썼다」로 치면, 쿠키가 깨진 사람이 영영 못 쓰게 된다.
    여기서 틀렸을 때의 손해는 한 번 더 써 보는 것뿐이라 관대한 쪽이 맞다.
    """
    moment = now if now is not None else int(time.time())
    try:
        used_s, expires_s, mac = (raw or "").split(".")
        used, expires = int(used_s), int(expires_s)
    except ValueError:
        return 0
    if not hmac.compare_digest(_sign(f"{used_s}.{expires_s}"), mac):
        return 0
    if expires <= moment:
        return 0
    return max(0, used)


def remaining(raw: str | None, now: int | None = None) -> int:
    """남은 게스트 검사 수. 화면이 이 값을 그대로 보여준다."""
    return max(0, FREE_CHECKS - used_count(raw, now))
