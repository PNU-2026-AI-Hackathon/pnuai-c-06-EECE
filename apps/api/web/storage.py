"""저장소가 재시작을 견디는지 **재서** 안다.

계정을 만들기로 한 이상, 계정이 사라질 수 있다는 사실을 조용히 둘 수 없다.
무료 플랜에는 영구 디스크를 붙일 수 없어서 재배포마다 DB 가 통째로 날아간다.

환경변수로 "영구임"이라고 적어 두는 방법도 있는데, 그건 **주장이지 사실이 아니다.**
적어 놓고 디스크를 안 붙이면 화면은 안전하다고 말하고 계정은 사라진다.
가장 나쁜 조합이다.

대신 **표식을 하나 남기고, 다음 기동 때 그게 살아 있는지 본다.**

- 처음 뜨면 표식이 없다 → `unknown`. **"안전하다"가 아니다** (헌법 2-2).
  진짜 처음인지 방금 지워진 건지 이 시점에는 구분할 방법이 없다.
- 다시 떴는데 표식이 있다 → `persistent`. 한 번이라도 재시작을 넘긴 것을
  우리가 직접 봤다는 뜻이다.
- 다시 떴는데 표식이 없다 → 구분이 안 되므로 여전히 `unknown` 이다.

그래서 이 값은 **`unknown` 에서 `persistent` 로만 간다.** 디스크를 붙이면
두 번째 기동부터 저절로 바뀌고, 아무도 코드를 안 고쳐도 된다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

#: DB 파일 옆에 둔다. DB 가 사는 곳이 곧 우리가 알고 싶은 곳이기 때문이다.
MARKER_SUFFIX = ".boot"

UNKNOWN = "unknown"
PERSISTENT = "persistent"


@dataclass(frozen=True)
class Storage:
    """저장소 상태.

    `state` 는 `unknown` 아니면 `persistent`. **`ephemeral` 이라는 값은 없다** —
    "안 살아남았다"를 확인할 방법이 없어서 그렇게 말할 수 없다.
    """

    state: str
    #: 이 저장소에서 관측한 기동 횟수. 1 이면 아직 재시작을 안 넘겼다.
    boots: int
    #: 표식이 처음 생긴 시각. 없으면 None.
    first_seen: str | None

    @property
    def survives_restart(self) -> bool:
        return self.state == PERSISTENT

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "boots": self.boots,
            "first_seen": self.first_seen,
            "survives_restart": self.survives_restart,
        }


def probe(db_path: str) -> Storage:
    """표식을 읽고, 갱신하고, 상태를 돌려준다. **기동 때 한 번 부른다.**

    표식을 못 쓰는 경우(읽기 전용 파일 시스템 등)에도 예외를 내보내지 않는다.
    저장소를 못 재는 것 때문에 서버가 안 뜨면 그게 더 큰 문제다.
    """
    marker = Path(db_path + MARKER_SUFFIX)
    now = datetime.now(timezone.utc).isoformat()

    previous = _read(marker)
    boots = int(previous.get("boots", 0)) + 1
    first_seen = previous.get("first_seen") or now

    _write(marker, {"boots": boots, "first_seen": first_seen, "last_boot": now})

    # 이전 기동의 표식을 실제로 봤을 때만 영구라고 말한다.
    state = PERSISTENT if previous else UNKNOWN
    return Storage(state=state, boots=boots, first_seen=first_seen)


def _read(marker: Path) -> dict:
    try:
        return json.loads(marker.read_text())
    except (OSError, json.JSONDecodeError):
        # 깨진 표식은 없는 것으로 친다 — 없는 쪽이 안전한 방향이다
        # (`unknown` 으로 떨어져 화면이 경고를 띄운다).
        return {}


def _write(marker: Path, body: dict) -> None:
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(body))
    except OSError:
        pass
