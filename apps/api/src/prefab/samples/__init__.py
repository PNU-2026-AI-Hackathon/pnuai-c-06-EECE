"""샘플 검사 (F-4) — 업로드 없이 결과부터 보여주는 경로.

**데모에서 첫 30초를 사는 파일이다.** 심사위원 앞에서 파일 세 개를 골라 올리고
기다리는 동안 이야기가 죽는다. 서버가 뜰 때 실측 보드 결과 하나를 미리 넣어 두면
프론트가 그 화면부터 띄울 수 있다.

    GET /api/v1/checks/chk_sample01

**새 엔드포인트가 아니다.** 계약(`docs/API_CONTRACT.md`)을 한 글자도 안 바꾼다 —
그냥 미리 만들어 둔 검사 하나가 조회되는 것뿐이다.

## 왜 서버가 켜질 때 엔진을 돌리지 않고 JSON 을 싣나

배포 이미지에 `tests/` 가 없다 (`.dockerignore`). 픽스처를 읽을 수 없다.
그래서 **미리 뽑아 둔 결과를 패키지 안에 싣는다.**

그러면 이 파일이 엔진보다 낡을 수 있다. 그 위험은 테스트로 막는다 —
`tests/test_samples.py` 가 픽스처로 결과를 다시 뽑아 이 파일과 대조한다.
어긋나면 CI 가 빨간불이다. **다시 뽑는 명령은 아래 한 줄이다.**

**다시 뽑는 명령은 두 줄이다.** 사실 DB 를 먼저 심고 그 DB 로 검사한다.

```bash
PREFAB_DB=/tmp/sample-facts.db python -m prefab --facts-load parts/*.json

PREFAB_DB=/tmp/sample-facts.db python -m prefab \
  tests/fixtures/esp32-c6-presence-smart-light.d356 \
  --bom tests/fixtures/esp32-c6-presence-smart-light.bom.csv \
  --firmware tests/fixtures/esp32-c6-presence-smart-light.firmware \
  --json > src/prefab/samples/check.sample.json
```

## 왜 사실을 넣고 뽑나 — 한 번 반대로 했다가 데었다

한동안 **일부러 사실 없이** 뽑았다. 이유는 "로컬 DB 상태가 섞이면 커밋된 파일만으로
재현할 수 없다" 였고 **그때는 맞는 말이었다.** 사실이 DB 에만 있었기 때문이다.

그 뒤 사실이 `parts/*.json` 으로 커밋됐고(배포에 영구 디스크를 안 쓰려고),
서버는 기동할 때 그것을 심는다. 그래서 이제 입력이 **커밋된 파일뿐**이고 결과가
결정적이다 — 낡은 근거만 그대로 남아 있었다.

결과가 이랬다.

    같은 보드를 직접 업로드   →  치명 2 · 경고 1 · **해제 2**
    업로드 없이 보는 샘플     →  치명 4 · 경고 1 · **해제 0**

**업로드 없이 보는 첫 화면에서만 우리 차별점이 사라져 있었다.**
데이터시트 근거로 경고를 지우는 것이 이 제품의 요점인데 그것만 안 보였다.
`tests/test_samples.py` 가 이제 같은 방식(커밋된 사실을 심어서)으로 대조한다.

"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: 샘플 검사의 고정 ID. 프론트가 이 값을 그대로 부른다.
SAMPLE_CHECK_ID = "chk_sample01"

SAMPLE_PATH = Path(__file__).parent / "check.sample.json"


def load_sample() -> dict[str, Any] | None:
    """미리 뽑아 둔 샘플 검사. 없거나 깨졌으면 None.

    **여기서 예외를 던지지 않는다.** 샘플은 있으면 좋은 것이지 서버가 뜨는 조건이
    아니다. 이것 때문에 배포가 죽으면 그게 훨씬 나쁘다.
    """
    try:
        data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or "check_id" not in data:
        return None
    return data
