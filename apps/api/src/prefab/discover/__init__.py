"""규칙 발견 — **우리 규칙이 못 본 것을 찾아 후보로 올린다.**

## 왜 이게 규칙 폴더 밖에 있나

`rules/` 안의 것은 **판정**이다. 순수 함수이고 LLM 을 안 부르고 같은 입력에 같은 답을 낸다
(헌법 2-1). 여기 있는 것은 판정이 아니라 **제안**이다. 섞으면 안 되므로 폴더를 나눴다.

    rules/      판정한다.  Finding 을 낸다.  검사 결과에 들어간다
    discover/   제안한다.  Candidate 를 낸다. 사람이 채택해야 규칙이 된다

## 근거가 있는 설계다

우리가 손으로 한 번 돌려 본 루프다. 같은 케이스를 LLM 에 던졌더니
**합성 케이스에서는 우리가 이겼는데 남의 실제 보드에서는 졌다** — LLM 오탐 0건,
우리 45건. 게다가 LLM 이 지적한 것 중 하나가 **진짜 결함**이었고, 우리 규칙 12개 중
어느 것도 그 모양을 안 보고 있었다. 그게 R14 가 됐다 (`_docs/규모_실험.md`).

그때 사람이 손으로 한 일을 제품이 하게 만드는 것이 이 모듈이다.

    LLM 이 이상한 자리를 제안한다  →  코드가 검증한다  →  사람이 채택한다

**가운데 단계가 이 모듈의 존재 이유다.** LLM 출력을 그대로 화면에 내보내면 그건
우리가 "안 한다" 고 적어둔 바로 그것이다.
"""

from .types import Candidate, Citation, Proposal
from .run import discover
from .verify import VerifyResult, verify

__all__ = ["Candidate", "Citation", "Proposal", "VerifyResult", "discover", "verify"]
