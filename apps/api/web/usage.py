"""원가와 사용량 — **우리가 돈을 쓰는 자리가 어디인지 세는 곳.**

요금을 정하려면 원가를 알아야 하는데, 이 서비스의 원가는 직관과 다르다.

- **검사는 사실상 공짜다.** 규칙은 순수 함수라 네트워크도 LLM 도 안 쓴다.
  한 번에 밀리초, 드는 것은 CPU 뿐이다.
- **돈이 드는 건 데이터시트를 읽는 일 하나뿐이다.** 부품 하나에 LLM 호출 한 번.
- 그리고 **그 비용은 부품마다 딱 한 번 든다.** 한 번 읽어 둔 사실은 그 뒤로
  모든 사용자, 모든 검사가 공짜로 쓴다.

그래서 검사가 늘어도 비용은 안 늘고, **부품 종류가 늘 때만** 는다. 세상의
부품 종류는 유한하고 우리 DB 는 단조증가하므로, 검사당 한계비용은 0 으로 간다.

이 파일은 그 주장을 **말이 아니라 DB 로** 뒷받침한다. 숫자를 손으로 적지 않는다 —
손으로 적은 숫자는 반드시 낡는다 (헌법 7절).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass


@dataclass
class Usage:
    """실측 사용량. **추정치가 하나도 없다.**"""

    #: 사실 DB 가 아는 부품 수. 데이터시트를 읽은 횟수와 같다 — 부품당 한 번.
    parts: int
    #: 그 부품들에서 뽑아 검증까지 통과한 사실의 수.
    facts: int
    #: 이 서버가 처리한 검사 수.
    checks: int
    #: 그 검사들에서 **사실이 덜어낸 오탐의 누계.**
    #: 데이터시트를 읽어 둔 덕분에 사용자가 안 봐도 됐던 경고의 수다.
    cleared_by_facts: int
    #: 사실 DB 를 만드느라 LLM 을 부른 횟수. 부품당 한 번이므로 `parts` 와 같다.
    #: 따로 두는 이유는 **이 둘이 갈라지면 원가 모델이 틀렸다는 뜻**이기 때문이다.
    #: 이 호출은 검사와 무관하게, 부품을 추가할 때 **미리** 일어난다.
    llm_calls_building_db: int

    @property
    def llm_calls_serving_checks(self) -> int:
        """검사를 처리하느라 부른 LLM 횟수. **구조적으로 0 이다.**

        비율로 말하지 않는 이유가 있다. 처음에는 "LLM 호출당 검사 몇 건"을
        실어 보냈는데, 갓 배포한 서버에서는 그 값이 1 보다 작게 나온다
        (부품 4개를 심어 뒀는데 검사는 1건). 숫자는 맞지만 **읽는 사람에게는
        원가가 안 빠진다는 뜻으로 보인다** — 실제로는 정반대인데도.

        비율이 낮은 건 검사가 아직 적어서일 뿐이고, 우리가 말하려는 것은
        애초에 비율이 아니다. 규칙은 순수 함수라서 검사는 밖으로 나가지
        않는다. 검사가 100만 건이어도 이 값은 0 이다.

        `tests/test_check_is_offline.py` 가 소켓을 막고 검사를 통째로 돌려
        이 0 을 지킨다. **말로만 적어 두면 언젠가 조용히 거짓이 된다.**
        """
        return 0

    def to_dict(self) -> dict:
        out = asdict(self)
        out["llm_calls_serving_checks"] = self.llm_calls_serving_checks
        return out


def collect(db_path: str) -> Usage:
    """DB 를 읽어 사용량을 센다.

    표가 아직 없을 수 있다 — 기동 직후이거나 검사가 한 번도 없었으면 그렇다.
    그때는 0 이다. **없는 표를 예외로 만들면 안내 화면 전체가 같이 죽는다.**
    """
    conn = sqlite3.connect(db_path)
    try:
        parts = _scalar(conn, "SELECT COUNT(DISTINCT mpn) FROM part_facts")
        facts = _scalar(conn, "SELECT COUNT(*) FROM part_facts")
        checks = _scalar(conn, "SELECT COUNT(*) FROM checks")
        cleared = _cleared(conn)
    finally:
        conn.close()

    return Usage(
        parts=parts,
        facts=facts,
        checks=checks,
        cleared_by_facts=cleared,
        llm_calls_building_db=parts,
    )


def _scalar(conn: sqlite3.Connection, sql: str) -> int:
    try:
        row = conn.execute(sql).fetchone()
    except sqlite3.OperationalError:
        return 0
    return int(row[0]) if row and row[0] is not None else 0


def _cleared(conn: sqlite3.Connection) -> int:
    """저장된 결과들에서 `summary.cleared` 를 더한다.

    합계를 따로 들고 있지 않고 매번 센다. 검사 수가 만 단위를 넘으면 느려질
    자리인데, **지금 그걸 미리 고치면 있지도 않은 문제를 위해 캐시를 하나
    더 두는 것**이라 안 한다. 느려지면 그때 표에 열을 하나 더 붙인다.
    """
    try:
        rows = conn.execute("SELECT payload FROM checks").fetchall()
    except sqlite3.OperationalError:
        return 0

    total = 0
    for (payload,) in rows:
        try:
            total += int(json.loads(payload).get("summary", {}).get("cleared", 0))
        except (json.JSONDecodeError, TypeError, ValueError):
            # 읽지 못한 결과 하나 때문에 전체 합계를 포기하지 않는다.
            continue
    return total
