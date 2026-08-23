"""요청 제한.

**여기에 HTTP 는 없다.** 시계를 주입받는 순수한 토큰 버킷이고, 그래서 테스트가
`sleep` 하지 않는다. HTTP 로 옮기는 일은 `app.py` 가 한다.

왜 필요한가. 배포는 무료 플랜이고 프로세스가 하나다. 검사 자체는 밀리초지만
업로드는 그렇지 않다 — 파일을 받아 파싱하는 동안 그 워커는 다른 요청을 못 받는다.
누가 반복해서 올리면 **서비스가 눕는 게 아니라 느려진다.** 눕는 건 눈에 보이지만
느려지는 건 안 보이고, 심사위원 눈에는 그냥 고장이다.

## 이게 막지 못하는 것 (헌법 2-4 — 못 한 일을 숨기지 않는다)

- **여러 IP 에서 오는 요청.** 주소별로 세기 때문에 주소를 바꾸면 그만이다.
- **프로세스가 여럿일 때.** 계수가 메모리에 있어서 워커마다 따로 센다.
  워커 N 개면 실효 한도가 N 배다. 지금은 워커가 하나라 맞지만, 늘리는 순간
  틀린다. 그때는 계수를 밖(Redis 등)으로 빼야 한다.
- **느린 고갈.** 한도 안쪽에서 꾸준히 부으면 못 막는다.

즉 이건 **사고와 장난을 막는 것**이지 공격을 막는 것이 아니다.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

#: 추적하는 주소 수의 상한.
#:
#: 주소마다 계수를 만들면 **그 사전 자체가 공격 표면이다** — 주소를 바꿔 가며
#: 부르면 메모리가 는다. 상한에 닿으면 가장 오래 조용했던 주소부터 버린다.
#: 버려진 주소는 한도가 초기화되지만, 그건 이미 오래 쉬었다는 뜻이라 손해가 없다.
MAX_TRACKED_CLIENTS = 10_000


@dataclass
class Bucket:
    """토큰 버킷 하나.

    `capacity` 개를 갖고 시작해 `per_seconds` 에 걸쳐 다시 찬다. 남은 토큰은
    소수로 둔다 — 정수로 깎으면 초당 한도가 1 미만인 창(시간당 한도 같은 것)에서
    영원히 차지 않는다.
    """

    capacity: int
    per_seconds: float
    tokens: float = field(default=-1.0)
    updated_at: float = 0.0

    def __post_init__(self) -> None:
        if self.tokens < 0:
            self.tokens = float(self.capacity)

    def _refill(self, now: float) -> None:
        if self.updated_at == 0.0:
            self.updated_at = now
            return
        elapsed = now - self.updated_at
        if elapsed <= 0:
            # 시계가 뒤로 갔다. 채우지도 깎지도 않는다 — 시계를 믿고 토큰을
            # 주면 시계를 흔들어 한도를 우회할 수 있다.
            self.updated_at = now
            return
        self.tokens = min(
            float(self.capacity),
            self.tokens + elapsed * (self.capacity / self.per_seconds),
        )
        self.updated_at = now

    def take(self, now: float) -> bool:
        """토큰 하나를 쓴다. 없으면 `False`. 없을 때는 **아무것도 깎지 않는다.**"""
        self._refill(now)
        if self.tokens < 1.0:
            return False
        self.tokens -= 1.0
        return True

    def retry_after(self, now: float) -> int:
        """다음 토큰까지 남은 초. 최소 1 — `Retry-After: 0` 은 즉시 재시도를 부른다."""
        self._refill(now)
        if self.tokens >= 1.0:
            return 0
        need = 1.0 - self.tokens
        seconds = need / (self.capacity / self.per_seconds)
        return max(1, int(seconds + 0.999))

    def remaining(self, now: float) -> int:
        self._refill(now)
        return int(self.tokens)


@dataclass
class Decision:
    """한 번의 판정. `allowed` 가 참이면 나머지는 안내용이다."""

    allowed: bool
    retry_after: int
    remaining: int
    #: 걸린 창의 이름 (`"분"` / `"시간"`). 통과했으면 `""`.
    window: str = ""


class RateLimiter:
    """주소별 이중 창 제한 — 짧은 폭주와 긴 고갈을 따로 막는다.

    창이 하나면 둘 중 하나를 못 막는다. 분당 한도만 두면 하루 종일 분당 한도를
    채워 부을 수 있고, 시간당 한도만 두면 한 번에 몰아쳐도 통과한다.
    """

    def __init__(
        self,
        *,
        per_minute: int,
        per_hour: int,
        clock=time.monotonic,
        max_clients: int = MAX_TRACKED_CLIENTS,
    ) -> None:
        if per_minute < 1 or per_hour < 1:
            raise ValueError("한도는 1 이상이어야 한다")
        self.per_minute = per_minute
        self.per_hour = per_hour
        self._clock = clock
        self._max_clients = max_clients
        self._clients: dict[str, tuple[Bucket, Bucket]] = {}

    @property
    def tracked(self) -> int:
        return len(self._clients)

    def _buckets(self, key: str, now: float) -> tuple[Bucket, Bucket]:
        found = self._clients.get(key)
        if found is not None:
            return found
        if len(self._clients) >= self._max_clients:
            self._evict(now)
        fresh = (
            Bucket(capacity=self.per_minute, per_seconds=60.0),
            Bucket(capacity=self.per_hour, per_seconds=3600.0),
        )
        self._clients[key] = fresh
        return fresh

    def _evict(self, now: float) -> None:
        """가장 오래 조용했던 10% 를 버린다.

        하나씩 버리면 상한에 닿은 뒤 매 요청마다 전체를 훑는다. 한 번에 덜어낸다.
        """
        drop = max(1, len(self._clients) // 10)
        stalest = sorted(self._clients.items(), key=lambda kv: kv[1][0].updated_at)
        for key, _ in stalest[:drop]:
            del self._clients[key]

    def check(self, key: str) -> Decision:
        """`key` 의 요청 하나를 판정한다. 통과하면 토큰을 쓴다.

        분 창을 먼저 본다. 분에서 막히면 **시간 창은 건드리지 않는다** — 막힌
        요청이 시간 한도를 깎으면 재시도가 재시도를 벌준다.
        """
        now = self._clock()
        minute, hour = self._buckets(key, now)

        if not minute.take(now):
            return Decision(
                allowed=False,
                retry_after=minute.retry_after(now),
                remaining=0,
                window="분",
            )
        if not hour.take(now):
            # 분 창에서 이미 하나 썼다. 돌려준다 — 시간 때문에 막힌 건데
            # 분 한도까지 깎이면 두 번 벌주는 셈이다.
            minute.tokens = min(float(minute.capacity), minute.tokens + 1.0)
            return Decision(
                allowed=False,
                retry_after=hour.retry_after(now),
                remaining=0,
                window="시간",
            )

        return Decision(
            allowed=True,
            retry_after=0,
            remaining=min(minute.remaining(now), hour.remaining(now)),
        )


# --------------------------------------------------------- 누구의 요청인가

def client_key(forwarded_for: str | None, peer: str | None) -> str:
    """요청을 셀 때 쓸 열쇠를 고른다.

    **`X-Forwarded-For` 의 맨 오른쪽을 쓴다. 맨 왼쪽이 아니다.**

    이 헤더는 프록시가 지나갈 때마다 **뒤에 덧붙인다.** 그래서 목록은

        [클라이언트가 스스로 적어 보낸 것들...], [우리 앞 프록시가 실제로 본 주소]

    꼴이 된다. 왼쪽은 요청을 보낸 쪽이 마음대로 적을 수 있다 — 흔히 쓰는
    "맨 왼쪽이 진짜 클라이언트" 규칙을 그대로 따르면 `X-Forwarded-For` 에
    아무 값이나 넣어 매 요청마다 새 한도를 받아 간다. **한도가 있으나 마나 된다.**

    맨 오른쪽은 우리 바로 앞의 프록시가 소켓에서 직접 본 주소라 위조할 수 없다.
    대신 프록시를 여럿 거치면 진짜 클라이언트가 아니라 중간 프록시를 세게 되고,
    그 뒤 사용자들이 한도를 나눠 쓰게 된다. 지금 배포는 앞에 프록시가 하나라
    맞는 선택이고, **틀리는 쪽이 안전한 방향**이다.

    헤더가 없으면 소켓 주소를 쓴다. 그것도 없으면(테스트 클라이언트 등)
    `"unknown"` 하나로 묶는다 — 묶이면 서로 한도를 나눠 쓰지만, 열쇠 없는
    요청을 무제한으로 통과시키는 것보다 낫다.
    """
    if forwarded_for:
        parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return peer or "unknown"
