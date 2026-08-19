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

```bash
python -m prefab tests/fixtures/esp32-c6-presence-smart-light.d356 \\
  --bom tests/fixtures/esp32-c6-presence-smart-light.bom.csv \\
  --firmware tests/fixtures/esp32-c6-presence-smart-light.firmware \\
  --json > src/prefab/samples/check.sample.json
```

부품 사실 DB(`--use-facts`)는 **일부러 안 넣었다.** 넣으면 이 파일이 로컬 DB 상태에
따라 달라져서, 커밋된 파일만으로는 다시 만들 수 없게 된다.
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
