# 마스터 프롬프트

> ⚠️ **이 문서는 이미 실행이 끝난 부트스트랩 프롬프트 아카이브입니다.**
> 그대로 다시 돌리지 마세요. 초기 구조를 어떻게 만들었는지 남겨둔 기록입니다.
>
> - **디자인 규약의 현재 진실**: [`apps/web/CLAUDE.md` 5절](../apps/web/CLAUDE.md)
>   과 [`apps/web/tailwind.config.js`](../apps/web/tailwind.config.js).
>   이 문서에 적혀 있던 색·폰트 값은 낡아서 지웠습니다.
> - **배포는 최우선이 아닙니다.** 아래 배포 관련 서술은 당시 판단이고, 지금은 후순위입니다.

---

빈 저장소에서 초기 구조를 세울 때 쓴 프롬프트.
`prefab-api`와 `prefab-web` 각각에서 한 번씩 실행한다. **두 사람이 동시에 시작할 수 있다.**

---

## 사전 준비 (5분)

GitHub에 저장소 두 개를 만들고 클론한 뒤, 아래 파일을 미리 배치한다.

```
prefab-api/
├─ CLAUDE.md                                   ← 받은 api/CLAUDE.md
├─ README.md                                   ← 받은 api/README.md
├─ API_CONTRACT.md                             ← DEV_PROMPTS.md 0절을 그대로 복사
├─ .claude/skills/prefab-rule/SKILL.md
├─ .claude/skills/prefab-datasheet/SKILL.md
└─ _incoming/
   ├─ parse_d356.py
   ├─ check.py
   └─ esp32c6presencesmartlight.d356

prefab-web/
├─ CLAUDE.md                                   ← 받은 web/CLAUDE.md
├─ README.md                                   ← 받은 web/README.md
├─ API_CONTRACT.md                             ← api와 동일한 파일
└─ _incoming/
   └─ prototype.html                           ← 디자인 톤 참고용
```

> `API_CONTRACT.md`는 **두 저장소에 같은 내용**으로 둔다. 바뀌면 양쪽을 함께 고친다.

---

# A. prefab-api 마스터 프롬프트

````
prefab-api 저장소를 처음부터 구축해서 배포까지 완료해줘.

시작 전에 CLAUDE.md와 API_CONTRACT.md를 반드시 읽고, 그 규범과 스펙을 정확히 따를 것.
특히 CLAUDE.md 2절(불변 원칙), 4절(범위 밖), 5절(IPC-D-356 오프셋),
6절(현재 실제 상태)을 지켜줘.

## 단계 1 — 패키지 이식

_incoming/ 의 parse_d356.py와 check.py를 아래 구조로 옮긴다.

src/prefab/
  types.py            Finding, Severity, Verdict, Evidence, Context
  netlist/d356.py     IPC-D-356 파서 (parse_d356.py 이식)
  netlist/graph.py    부품·네트 그래프, X좌표 패드 클러스터링
  firmware/__init__.py    빈 스텁
  datasheet/__init__.py   빈 스텁
  rules/__init__.py       레지스트리
  rules/r11_net_name_domain.py
  rules/r12_cross_domain.py
  engine.py           규칙 실행 → Finding 수집 → 정렬
web/app.py
tests/fixtures/esp32c6presencesmartlight.d356

### types.py 계약 — 반드시 이대로

.claude/skills/prefab-rule/SKILL.md 의 예제 코드가 수정 없이 동작해야 한다.

- Severity: CRITICAL / WARNING / INFO
- Verdict:  FAIL / PASS / UNRESOLVED
- Evidence: Evidence.netlist(text, highlight=[])
            Evidence.firmware(file, line, snippet, highlight=[])
            Evidence.datasheet(mpn, table, page, quote)
- Finding:  rule, title, tier, severity, verdict, net, claim,
            evidence[], suggestion, unresolved_reason
- Context:  .netlist / .firmware / .datasheet / .git
            firmware와 datasheet는 None일 수 있다

각 규칙 모듈은 RULE_ID, TITLE, SEVERITY, TIER, NEEDS, check(ctx) 를 노출한다.
엔진은 NEEDS에 선언된 입력이 없으면 그 규칙을 실행하지 않고 "skipped"로 기록한다.
조용히 통과시키지 말 것.

### 이식 원칙

판정 로직을 의미 그대로 옮긴다. 개선하지 않는다.
알려진 버그(R11·R12가 같은 네트에 중복 검출)는 이번에 고치지 말고
xfail 테스트로 남긴다. 이식이 동작을 바꾸지 않았음을 먼저 증명해야 한다.

### 골든 테스트 (통과 못 하면 이식 실패)

test_real_board_findings():
  - 정확히 3건: R11 PRESENCE_3V3, R12 PRESENCE_3V3, R12 _IN_ACTIVE_LOW
  - 부품 10개, 네트 8개 (N/C 제외)
  - K1의 6개 패드가 X좌표로 두 그룹(제어부/스위치부)으로 분리됨

규칙당 테스트 3개도 함께: 양성 / 음성 / 미해결

## 단계 2 — API 구현

API_CONTRACT.md의 스펙을 정확히 구현한다. 스펙에 없는 필드를 추가하지 않는다.

POST /api/v1/checks
  - multipart: netlist(필수) / bom(선택) / firmware(선택)
  - 크기 제한 10MB, 확장자 검증, 넷리스트 없으면 422
  - 동기 실행. 지금 규모에서 큐는 불필요하다
GET  /api/v1/checks/{id}     계약의 전체 응답. 없으면 404
GET  /api/v1/rules           미구현 규칙도 implemented:false 로 포함
GET  /healthz

### pipeline 필드가 이 API의 핵심이다

각 단계의 status를 정확히 채운다.
- BOM 없음 → 4·5단계 skipped, detail "BOM 없음"
- 펌웨어 없음 → 3단계 skipped, firmware를 NEEDS로 선언한 규칙은 미실행
  summary.rules_skipped 에 반영
- 못 돌린 규칙이 있는데 "이상 없음"처럼 보이는 응답은 만들지 않는다

저장소는 SQLite 하나 (checks, part_facts).
업로드 파일은 임시 디렉터리, 24시간 후 삭제하는 정리 작업 포함.
CORS: 프론트 origin과 http://localhost:5173 허용.

## 단계 3 — 배포

Dockerfile 또는 nixpacks 중 빠른 쪽으로 Railway에 배포한다.
배포 후 실제 URL에 픽스처를 POST 해서 3건이 그대로 나오는지 확인한다.

curl -F "netlist=@tests/fixtures/esp32c6presencesmartlight.d356" \
     https://<host>/api/v1/checks

## 단계 4 — CI

.github/workflows/ci.yml — pytest만. 푸시마다 실행.

## 하지 말 것

- 새 규칙 추가, 판정 로직 "개선"
- 인증 / 회원가입 / 결제
- Postgres / Redis / Celery / 마이크로서비스
- 계약에 없는 응답 필드
- README.md 를 덮어쓰는 것 (이미 작성되어 있다. 상태 표만 실제 값으로 갱신)

## 보고

작은 단위로 커밋을 쪼갠다. 커밋 메시지는 한국어 한 줄.
끝나면 다음을 보여줘:
  1. pytest 결과
  2. 배포 URL
  3. 실제 URL에 픽스처를 POST 한 응답 JSON 전문
  4. CLAUDE.md 6절(현재 실제 상태)에서 갱신이 필요한 항목
````

---

# B. prefab-web 마스터 프롬프트

````
prefab-web 저장소를 처음부터 구축해서 Vercel 배포까지 완료해줘.

시작 전에 CLAUDE.md와 API_CONTRACT.md를 반드시 읽고 따를 것.
_incoming/prototype.html 은 디자인 톤 참고용이다.
톤만 가져오고, 거기 적힌 수치는 전부 허구이므로 하나도 옮기지 않는다.

## 스택

Vite + React + TypeScript + Tailwind. pnpm.
상태관리 라이브러리, 차트 라이브러리, UI 킷 사용 금지. fetch + useState로 충분하다.

## 단계 1 — 목 데이터로 화면 완성 (백엔드를 기다리지 않는다)

API_CONTRACT.md의 예시 응답을 src/mocks/check.json 으로 저장하고,
VITE_API_BASE 가 비어 있으면 목을 쓰도록 한다.
응답 타입은 src/types/api.ts 에 계약 그대로 정의한다.

### 화면 3개

/  업로드
   - 슬롯 3개: 넷리스트(필수) / BOM(선택) / 펌웨어 zip(선택)
   - 드래그앤드롭 + 파일 선택 버튼 둘 다
   - 선택 항목이 비면 warn 색으로 무엇을 못 하게 되는지 명시
     BOM 없음 → "부품 식별 불가 · 오탐 증가"
     펌웨어 없음 → "코드 대조 규칙 5개 실행 불가"
   - "샘플 보드로 실행" 버튼 (심사 시연용, 필수)

/c/{check_id}  처리 중
   - pipeline 배열을 순서대로 렌더, 1초 폴링
   - status별 색은 CLAUDE.md 5절의 ok / warn / crit 토큰을 쓴다. skipped는 detail 노출
   - skipped 단계를 흐리게 숨기지 말 것. 사유를 그대로 보여준다

/r/{check_id}  리포트  — 구조는 Chrome Lighthouse 리포트를 따른다
   1. 요약 타일 3개: 치명 / 확인 필요 / 해제됨
   2. 입력 요약: 무엇을 받았고 무엇이 없어서 무엇을 못 했는지
   3. 발견 목록 (severity 순)
      verdict === "PASS" 인 항목은 Lighthouse의 "통과한 감사"처럼 접어서 하단에
   4. 넷리스트 부록 (mono, 발견에 연루된 네트는 crit 강조)

### 시그니처 컴포넌트 — 발견 카드

제품의 얼굴이다. 여기에 공을 들일 것.

> 이 절에 있던 2열 + 세로 이음매 설계는 **폐기됐습니다.**
> 가로축이 "핀 순서"와 "회로도/코드"라는 두 의미를 동시에 져서 근거가 잘못된 쪽에 놓였습니다.
> 지금은 **소스마다 한 줄(레인)** 구조입니다.
> 현재 명세는 [`apps/web/CLAUDE.md` 4절](../apps/web/CLAUDE.md)에 있습니다.

## 단계 2 — 디자인 시스템

[`apps/web/CLAUDE.md` 5절](../apps/web/CLAUDE.md)의 토큰을 `tailwind.config.js`에 등록한다.

> 원래 여기에 색·폰트 값이 그대로 적혀 있었습니다. 디자인을 바꾸자 이 사본이 거짓말이 됐고,
> 같은 값이 5개 문서에 흩어져 있어 전부 어긋났습니다. **그래서 값을 지우고 링크만 남깁니다.**
> 값은 `tailwind.config.js` 하나에만 존재합니다.

- 넷리스트·핀·코드·규칙 ID는 전부 mono
- 애니메이션은 파이프라인 진행 하나만. prefers-reduced-motion 존중

## 단계 3 — 실제 API 연결

VITE_API_BASE 가 있으면 실제 API를 호출한다.
업로드 → 폴링 → 리포트 흐름이 목과 동일하게 동작해야 한다.
실패 상태(422, 404, 500, 네트워크 오류)를 각각 처리한다.
에러 문구는 무엇이 잘못됐고 어떻게 고치는지 알려준다. 사과하지 않는다.

## 단계 4 — 배포 (후순위)

지금은 배포를 최우선으로 두지 않습니다. `VITE_API_BASE`가 비면 목 데이터로 돌기 때문에
화면 작업이 배포를 기다리지 않습니다. 붙일 준비만 해두고, 규칙과 화면을 먼저 끝냅니다.

## 절대 하지 말 것

- 숫자를 지어내는 것. API가 0을 주면 0, null이면 "—"
- prototype.html 의 허구 수치(부품 DB 418개 등)를 옮기는 것
- 로그인 / 회원가입 / 결제 / 가격표 / 마케팅 히어로 섹션
- 계약에 없는 필드를 가정하는 것
- README.md 덮어쓰기 (이미 작성되어 있다)

## 접근성 기본선

키보드 포커스 보이게, 색상만으로 심각도 구분하지 말 것(배지 텍스트 병행), 375px까지 유지.

## 보고

작은 단위로 커밋. 커밋 메시지는 한국어 한 줄.
끝나면 Vercel URL과 각 화면 스크린샷을 보여줘.
````

---

# C. 완료 검수 체크리스트

두 프롬프트가 끝나면 이걸로 확인한다. 하나라도 아니면 아직 안 끝난 것이다.

**백엔드**
- [ ] `pytest -q` 전부 통과 (중복 건은 xfail)
- [ ] 골든 테스트 통과 — 실제 보드에서 정확히 3건
- [ ] 배포 URL의 `/healthz` 가 200
- [ ] 실제 URL에 픽스처 POST → 3건이 그대로 나옴
- [ ] BOM 없이 보냈을 때 `pipeline` 4·5단계가 `skipped` + 사유 포함
- [ ] `/api/v1/rules` 에 미구현 규칙 10개가 `implemented:false` 로 나옴

**프론트엔드**
- [ ] Vercel URL이 열림, 로그인 없이 접근됨
- [ ] "샘플 보드로 실행"이 동작
- [ ] 발견 카드에 가운데 이음매가 보임
- [ ] `skipped` 단계가 사유와 함께 보임 (숨겨지지 않음)
- [ ] 375px 폭에서 깨지지 않음
- [ ] **화면 어디에도 지어낸 숫자가 없음**

**둘 다**
- [ ] `API_CONTRACT.md` 가 양쪽에 동일하게 있음
- [ ] CORS 통과 — 프론트에서 실제 API 호출 성공
- [ ] `git shortlog -sn` 에 팀원들이 각자 나옴

---

# D. 그다음

| 시점 | 백엔드 | 프론트 |
|---|---|---|
| **D-11 (8/18)** | **API 배포 완료** | **Vercel 배포 완료** |
| D-10 (8/19) | 실제 연결, CORS, R11·R12 중복 수정 | 실제 API 연결 |
| D-9~8 | 펌웨어 파서 → R1·R5·R7·R8 | 발견 카드 다듬기 |
| D-7~6 | 데이터시트 파이프라인 → R4 | "해제됨" 표현, 근거 링크 |
| D-5 | 검증 데이터셋 스크립트 | 반응형·접근성 마무리 |
| D-4~3 | GitHub Action (여유되면) | 발표 영상 촬영 |

**8/18 밤까지 양쪽 URL이 살아 있어야 한다.**
심사기준 3번이 "본선 기간 내 실제 구동 및 배포"를 본다. 기능보다 배포가 먼저다.
