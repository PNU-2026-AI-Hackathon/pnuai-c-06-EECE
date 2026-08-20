"""커밋된 부품 사실 파일(`parts/*.json`)을 DB 로 심는다.

**왜 패키지 안에 있나.** 원래 `web/service.py` 에만 있었다. 그런데 이 함수는
웹과 무관하다 — 샘플 검사를 다시 뽑을 때도, CLI 로 검사할 때도 같은 일이 필요하다.
한쪽에만 있으면 다른 쪽이 **사실 없이** 결과를 만들고, 그 결과가 커밋된다.

실제로 그렇게 됐다. 서버는 사실을 심고 도는데 샘플 JSON 은 사실 없이 뽑혀서,
**업로드 없이 보는 첫 화면에서만 데이터시트 해제가 0건**이었다. 같은 보드를
직접 올리면 2건이 해제되는데도 그랬다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .store import FactStore

#: 서식 파일은 사실이 아니다. `_` 로 시작하는 파일은 건너뛴다.
TEMPLATE_PREFIX = "_"


def seed_facts(facts_dir: "Path | str", store: "FactStore") -> list[str]:
    """부품 사실 파일을 DB 에 심고, 넣은 부품번호 목록을 돌려준다.

    `prefab.db` 는 `.gitignore` 라서 배포 이미지에 DB 가 없다. 그러면 데이터시트
    해제(R11·R12)가 배포된 서버에서 통째로 안 돈다 — **차별점이 데모에서만 사라진다.**
    커밋된 진실은 `parts/*.json` 뿐이므로(CLAUDE.md 6절) 그것으로 다시 만든다.
    그래서 **영구 디스크가 필요 없다.**

    **실패해도 조용히 넘어간다.** 사실 하나 때문에 서버가 안 뜨면 그게 훨씬 나쁘다.
    대신 무엇을 넣었는지 돌려주므로 부른 쪽이 그 사실을 노출할 수 있다 (헌법 2-4).

    **결정적이다.** 입력이 커밋된 파일뿐이고 정렬된 순서로 읽는다. 그래서 이걸로
    만든 결과는 커밋된 것만으로 다시 만들 수 있다 — 로컬 DB 상태가 안 섞인다.
    """
    folder = Path(facts_dir)
    if not folder.is_dir():
        return []
    loaded: list[str] = []
    for path in sorted(folder.glob("*.json")):
        if path.stem.startswith(TEMPLATE_PREFIX):
            continue
        try:
            text = path.read_text(encoding="utf-8")
            store.save_json(text)
            # 부품번호는 파일 안에 있다. 파일명은 소문자라 조회 키와 다르다.
            mpn = json.loads(text).get("mpn") or path.stem
        except Exception:  # noqa: BLE001 - 사실 하나 때문에 서버가 죽으면 안 된다
            continue
        loaded.append(mpn)
    return loaded
