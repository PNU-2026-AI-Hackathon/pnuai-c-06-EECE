---
name: prefab-orient
description: Prefab 저장소에서 상태를 파악하거나 파일을 찾을 때 제일 먼저 쓴다. "지금 어디까지 됐어", "리포 구조 알려줘", "이 프로젝트 뭐야", "~ 어디 있어", "무슨 파일 봐야 해", "상태 정리해줘", "전체 훑어줘" 같은 요청, 그리고 여러 파일을 읽어야 할 것 같을 때. 이 저장소는 문서가 2200줄이고 node_modules가 3700개 파일이라 탐색 방법을 틀리면 아무것도 못 하고 컨텍스트가 찬다. 어디를 읽고 어디를 읽지 말지, 무슨 명령으로 대신할지를 알려준다.
---

# Prefab 저장소 탐색

**이 스킬 자체도 토큰을 쓴다.** 그래서 짧다. 원칙 하나뿐이다 —
*읽기 전에 세어보고, 통째로 읽는 대신 뽑아 읽는다.*

---

## 1. 지뢰 세 개

| 하지 말 것 | 왜 | 대신 |
|---|---|---|
| `ls -R` · `find .` | `apps/web/node_modules`에 파일 3,746개 | `git ls-files \| grep -v node_modules` (54개) |
| 큰 JSON을 Read | 목·목표 응답이 각각 500줄 넘는다 | 아래 2절 요약 명령 |
| `_docs/` 전부 읽기 | 문서 2,200줄. 대부분 프롬프트 아카이브 | 아래 3절 라우팅 표 |

---

## 2. 큰 파일은 뽑아 읽는다

검사 결과 JSON(목·목표 응답·계약 예시)은 구조가 같다. 통째로 Read하지 말고:

```bash
python3 -c "
import json,sys; d=json.load(open(sys.argv[1]))
print(d['check_id'], d['status'], json.dumps(d['summary'],ensure_ascii=False))
print([(f['rule'],f['severity'],f['verdict'],f.get('net')) for f in d['findings']])
print([(p['step'],p['status'],p['detail']) for p in d['pipeline']])
" apps/web/src/mocks/check.json
```

넷리스트(`.d356`)도 마찬가지다. 76줄이라 읽어도 되지만, 네트별로 보려면:

```bash
grep -n "NET이름" apps/api/tests/fixtures/*.d356
awk '/^3/{print substr($0,4,14)}' <파일> | sort | uniq -c | sort -rn   # 네트별 레코드 수
```

---

## 3. 무엇을 알고 싶으면 어디 한 곳만

| 알고 싶은 것 | 읽을 곳 | 읽지 말 곳 |
|---|---|---|
| 제품이 뭐고 지금 상태가 어떤가 | `README.md` "현재 상태"·"규칙 카탈로그" 절 | `_docs/*` 전부 |
| API 응답 모양 | `docs/API_CONTRACT.md` + `apps/web/src/types/api.ts` | 목 JSON 통째로 |
| 화면 규약·디자인 | `apps/web/CLAUDE.md` (값은 `tailwind.config.js`) | 다른 문서의 디자인 절 (사본이다) |
| 백엔드 규약·파서 지식 | `apps/api/CLAUDE.md` | — |
| R7·R8이 무엇을 잡아야 하는가 | `apps/api/tests/fixtures/*.EXPECTED.md` | — |
| 백엔드에 뭘 요청해뒀나 | `_docs/백엔드_요청서.md` | 나머지 `_docs/*` |
| 핀 번호·칩 표 | `docs/CHIPS.md` | 규칙 코드 (핀은 코드에 없다) |

`_docs/MASTER_PROMPT.md` · `DEV_PROMPTS.md` · `PROMPTS.md` · `BOOTSTRAP.md`는
**프롬프트 아카이브다.** 현재 상태를 묻는 질문의 답은 여기 없다. 명시적으로 요청받을 때만 연다.

> 문서가 서로 어긋나면 **코드가 이긴다.** 규칙 카탈로그는 세 문서에 복사돼 있고 이미 갈라져 있다
> (`apps/api/CLAUDE.md`의 R1·R5는 칩 번호가 하드코딩돼 있어 README와 다르다).

---

## 4. 도구 함정

```bash
# pnpm 스크립트는 install 게이트(ignored build scripts)에서 죽는다. 바이너리를 직접 부른다
cd apps/web && ./node_modules/.bin/tsc --noEmit
cd apps/web && ./node_modules/.bin/vite build
```

**브라우저 프리뷰**: 패널이 숨겨져 있으면 `innerWidth`가 `0`으로 잡히고
`getBoundingClientRect`가 전부 거짓값을 준다 (카드 높이가 6000px로 나온다).
측정하거나 스크린샷을 찍기 전에 **`resize_window`로 뷰포트를 명시한다.**
스크롤은 JS(`scrollTo`)와 스크린샷이 어긋날 수 있으니, 한 화면에 담기는 높이로 뷰포트를 키우는 편이 싸다.

**목 두 벌**: `/r/chk_sample01`(실제 결과) · `/r/chk_target01`(목표 응답 명세).
id는 각 JSON의 `check_id`에서 확인한다 — 계약 문서의 예시 id와 다르다.

---

## 5. 상태를 물으면 이 순서로 답한다

1. `git log --oneline -8` · `git status --short` — 무슨 일이 있었나
2. `git ls-files | grep -v node_modules` — 실제로 뭐가 있나
3. `README.md`의 "현재 상태"·"알려진 문제" 절

**문서가 있다고 코드가 있는 게 아니다.** README는 `apps/api/src/prefab/` 구조를 그려두었지만
지금 존재하는 백엔드는 `apps/api/_incoming/`의 스크립트 두 개뿐이다.
상태를 보고할 때는 문서가 아니라 `git ls-files` 결과를 근거로 말한다.
