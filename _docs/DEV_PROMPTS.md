# Prefab — 프론트/백 개발 프롬프트

전제: `BOOTSTRAP.md`의 Phase 0이 끝나 패키지 구조와 R11·R12가 동작하는 상태.

저장소는 두 개로 나눈다.
- `prefab-api` — FastAPI, Railway/Render 배포
- `prefab-web` — React, Vercel 배포

---

# 0. API 계약 — 코딩 전에 이것부터 합의

**이 문서를 양쪽 저장소에 같은 파일로 복사해 둔다.** 계약이 바뀌면 양쪽을 동시에 고친다.

## 엔드포인트

```
POST   /api/v1/checks          검사 생성 (multipart)
GET    /api/v1/checks/{id}     결과 조회
GET    /api/v1/rules           규칙 카탈로그
GET    /healthz                헬스체크
```

### POST /api/v1/checks

multipart/form-data

| 필드 | 필수 | 설명 |
|---|---|---|
| `netlist` | ✅ | IPC-D-356 파일 (.d356/.ipc/.txt) |
| `bom` | ✕ | 부품 목록 CSV (refdes, mpn, manufacturer, value) |
| `firmware` | ✕ | 펌웨어 소스 zip |

응답 `201`
```json
{ "check_id": "chk_7f3a2b", "status": "running" }
```

### GET /api/v1/checks/{id}

```json
{
  "check_id": "chk_7f3a2b",
  "status": "done",
  "created_at": "2026-08-18T11:20:00Z",
  "inputs": {
    "netlist": { "filename": "board.d356", "nets": 8, "parts": 10 },
    "bom": null,
    "firmware": null
  },
  "summary": {
    "critical": 1, "warning": 1, "cleared": 1,
    "rules_run": 2, "rules_skipped": 10,
    "parts_identified": 0, "parts_total": 10
  },
  "pipeline": [
    { "step": 1, "name": "넷리스트 파싱",     "status": "done",    "detail": "네트 8 · 부품 10" },
    { "step": 2, "name": "부품 식별",         "status": "partial", "detail": "BOM 없음 · 좌표 클러스터링만" },
    { "step": 3, "name": "펌웨어 정적 분석",  "status": "skipped", "detail": "펌웨어 미제출" },
    { "step": 4, "name": "데이터시트 수집",   "status": "skipped", "detail": "BOM 없음" },
    { "step": 5, "name": "전기적 사실 추출",  "status": "skipped", "detail": "데이터시트 없음" },
    { "step": 6, "name": "규칙 엔진",         "status": "done",    "detail": "12개 중 2개 실행" },
    { "step": 7, "name": "리포트 생성",       "status": "done",    "detail": null }
  ],
  "findings": [ /* 아래 */ ],
  "netlist": {
    "nets": [ { "name": "PRESENCE_3V3", "vias": 2,
                "connections": [ {"ref":"U1","pin":"LP-G"}, {"ref":"U2","pin":"OUT"} ] } ],
    "parts": [ { "ref": "U2", "pins": ["GND","OUT","UART","VCC"], "mpn": null } ]
  }
}
```

`status`: `running` | `done` | `failed`
`pipeline[].status`: `done` | `partial` | `skipped` | `failed`

> **`skipped`를 조용히 숨기지 않는다.** 무엇을 못 했는지 보이는 것이 이 제품의 신뢰다.

### finding 객체

```json
{
  "rule": "R12",
  "title": "상위 전원 도메인이 하위를 직결",
  "tier": "기본",
  "severity": "CRITICAL",
  "verdict": "FAIL",
  "net": "PRESENCE_3V3",
  "claim": "5V로 동작하는 부품의 출력이 3.3V 핀에 직결되어 있습니다. 중간에 아무것도 없습니다.",
  "evidence": [
    { "kind": "netlist",   "text": "U2.VCC → 5V_BUS\nU2.OUT → PRESENCE_3V3\nU1.LP-G → PRESENCE_3V3",
      "highlight": ["5V_BUS"] },
    { "kind": "firmware",  "file": "src/main.cpp", "line": 44,
      "snippet": "pinMode(PRESENCE_PIN, INPUT);", "highlight": ["PRESENCE_PIN"] },
    { "kind": "datasheet", "mpn": "HLK-LD2410C", "table": "Electrical Characteristics",
      "page": 3, "quote": "OUT high level output voltage 3.3V" }
  ],
  "suggestion": "U2의 부품번호를 제출하면 데이터시트로 안전 여부를 판정합니다.",
  "unresolved_reason": "U2 미식별 — BOM 필요"
}
```

- `severity`: `CRITICAL` | `WARNING` | `INFO`
- `verdict`: `FAIL` | `PASS` | `UNRESOLVED`
- `tier`: `기본` | `차별`
- `evidence[].kind`: `netlist` | `firmware` | `datasheet`
- 값이 없으면 `null`. 빈 문자열이나 `"N/A"`로 채우지 않는다.

## 디자인 토큰 — 양쪽 공유

```
vellum      #E6E9E4    제도 용지 (배경)
vellum-2    #F2F4F0    카드 배경
ink         #171C26    제도 잉크 (본문)
graphite    #6E7683    보조 텍스트
hair        #C3C9C1    헤어라인
redpen      #C0322A    교정 빨간펜 · CRITICAL · 이음매
amber       #A9700F    WARNING · skipped
verify      #2C6248    PASS · cleared
font-sans   'IBM Plex Sans KR'
font-cond   'IBM Plex Sans Condensed'   라벨 · 대문자 · letter-spacing
font-mono   'IBM Plex Mono'             넷리스트 · 코드 · 핀 이름
```

---

# 1. 백엔드 프롬프트 (`prefab-api`)

````
prefab-api를 만들어줘. CLAUDE.md를 먼저 읽고 그 규범을 따를 것.
API_CONTRACT.md의 스펙을 정확히 구현한다. 스펙에 없는 필드를 추가하지 않는다.

## 범위

- FastAPI + uvicorn. Python 3.11+
- Phase 0에서 만든 src/prefab 패키지를 그대로 사용. 로직을 다시 쓰지 않는다
- 저장소: SQLite 한 개 (checks, part_facts)
- 업로드 파일은 임시 디렉터리. 24시간 후 삭제하는 정리 작업 포함
- CORS: 프론트 origin과 localhost:5173 허용

## 엔드포인트

POST /api/v1/checks
  - multipart 수신, 크기 제한 10MB, 확장자 검증
  - 넷리스트는 필수. 없으면 422
  - 검사를 동기로 실행 (지금 규모에서는 큐가 불필요하다).
    5초를 넘길 것 같으면 그때 BackgroundTasks로 바꾼다
  - check_id 생성 후 201

GET /api/v1/checks/{id}
  - 계약의 전체 응답 반환
  - 없으면 404

GET /api/v1/rules
  - 규칙 카탈로그: id, title, tier, severity, needs, implemented(bool)
  - 미구현 규칙도 implemented:false 로 포함한다. 숨기지 않는다

GET /healthz

## pipeline 필드가 핵심이다

각 단계의 status를 정확히 채운다.
- BOM이 없으면 4·5단계는 skipped, detail에 "BOM 없음"
- 펌웨어가 없으면 3단계 skipped, 그리고 firmware를 NEEDS로 선언한 규칙들은
  실행하지 않고 summary.rules_skipped 에 반영한다
- 규칙을 못 돌렸는데 "이상 없음"처럼 보이게 하는 응답은 만들지 않는다

## 배포

- Dockerfile 또는 nixpacks 중 빠른 쪽
- Railway 배포까지 완료하고 공개 URL을 알려줘
- 배포 후 tests/fixtures/esp32c6presencesmartlight.d356 을 실제 URL에 POST 해서
  R11 PRESENCE_3V3 / R12 PRESENCE_3V3 / R12 _IN_ACTIVE_LOW 3건이 나오는지 확인

## 하지 말 것

- 인증, 회원가입, 결제
- Postgres, Redis, Celery
- 판정 로직 수정 (규칙은 src/prefab/rules 에서만 바뀐다)
- 계약에 없는 응답 필드

작은 커밋으로 쪼개고, 마지막에 배포 URL과 실제 응답 JSON을 보여줘.
````

---

# 2. 프론트엔드 프롬프트 (`prefab-web`)

````
prefab-web을 만들어줘. API_CONTRACT.md의 응답 스펙과 디자인 토큰을 따른다.

## 스택

- Vite + React + TypeScript, Tailwind
- 상태관리 라이브러리 없이. fetch + useState 로 충분하다
- Vercel 배포
- 인증 없음. 결과는 URL만으로 열린다

## 화면 3개

### / — 업로드
- 슬롯 3개: 넷리스트(필수) · BOM(선택) · 펌웨어 zip(선택)
- 드래그앤드롭 + 파일 선택 둘 다
- 선택 항목이 비면 주황(amber)으로 "무엇을 못 하게 되는지" 명시.
  BOM 없음 → "부품 식별 불가 · 오탐 증가"
  펌웨어 없음 → "코드 대조 규칙 5개 실행 불가"
- "샘플 보드로 실행" 버튼: 번들된 예제 넷리스트로 즉시 실행 (심사 시연용, 필수)

### /c/{check_id} — 처리 중
- pipeline 배열을 순서대로 렌더
- status별 표시: done=verify색 / partial=amber / skipped=amber+취소선 아님, 사유를 그대로 노출 / failed=redpen
- skipped 단계를 흐리게 숨기지 말 것. detail 문구를 그대로 보여준다
- 1초 폴링, status가 done이면 리포트로 전환

### /r/{check_id} — 리포트
구조는 Chrome Lighthouse 리포트를 따른다.

1. 요약 타일 3개: 치명 / 확인 필요 / 해제됨
2. 입력 요약: 무엇을 받았고 무엇이 없어서 무엇을 못 했는지
3. 발견 목록 — severity 순. verdict=PASS(해제됨) 항목은
   Lighthouse의 "통과한 감사"처럼 **접어서 하단에** 둔다
4. 넷리스트 부록 (monospace, 발견에 연루된 네트는 redpen 강조)

## 발견 카드 — 시그니처 컴포넌트

이 컴포넌트가 제품의 얼굴이다. 공들일 것.

- 상단 바: severity 배지 · 규칙 ID(mono) · 네트명(mono) · tier 배지
- claim: 한 문장, 볼드, 15~16px
- **본문은 좌우 2열이고 가운데에 redpen 1.5px 세로선(이음매)이 지난다**
  - 좌: kind=netlist 근거
  - 우: kind=firmware 또는 datasheet 근거
  - highlight 배열의 토큰은 redpen 밑줄 + 연한 배경
  - 근거가 한쪽뿐이면 그 열만 채우고 이음매는 유지한다
- 하단: suggestion. unresolved_reason 이 있으면 amber 배경, 없으면 verify 배경
- 모바일에서는 2열이 위아래로 쌓이고 이음매는 가로선이 된다

## 디자인

- 제도 용지 톤. 배경에 22px 미세 격자 (rgba(23,28,38,.035))
- 라벨은 font-cond 대문자 letter-spacing .16em
- 넷리스트·핀·코드는 전부 font-mono
- border-radius 0. 모서리를 둥글리지 않는다
- 애니메이션은 파이프라인 진행 하나뿐. prefers-reduced-motion 존중
- 헤더는 도면 표제란 형태 (좌: 제품명 / 우: 메타 3칸 격자)

## 절대 하지 말 것

- 숫자를 지어내지 말 것. API가 0을 주면 0으로 표시한다.
  "부품 DB 418개" 같은 placeholder를 넣지 않는다
- 값이 null이면 "—" 로 표시하고 추정하지 않는다
- 인증 화면, 랜딩 히어로 섹션, 가격표
- 차트 라이브러리 (요약은 숫자 타일로 충분하다)

## 접근성 기본선

키보드 포커스 보이게, 색상만으로 심각도를 구분하지 말 것(배지 텍스트 병행),
모바일 375px까지 깨지지 않게.

Vercel 배포까지 하고 URL을 알려줘.
````

---

# 3. 병렬 작업 규칙

분리했을 때 시간을 까먹는 세 가지를 미리 막는다.

**하나. 계약을 먼저 고정한다.** `API_CONTRACT.md`를 양쪽 저장소에 커밋하고 시작한다.
바꿔야 하면 양쪽 담당이 같이 고친다. 한쪽이 임의로 필드를 추가하지 않는다.

**둘. 프론트는 목 응답으로 먼저 만든다.** 백엔드를 기다리지 않는다.
계약의 예시 JSON을 `src/mocks/check.json` 으로 두고 그걸로 화면을 완성한 뒤,
`VITE_API_BASE` 환경변수로 실제 API에 붙인다.

**셋. CORS는 첫날 뚫어둔다.** 배포 직전에 발견하면 반나절이 날아간다.
백엔드 첫 커밋에 CORS 미들웨어를 넣고, 프론트 로컬(5173)에서 실제 API 호출이
되는 것을 확인한 뒤 다음으로 넘어간다.

---

# 4. 순서

| 시점 | 백엔드 | 프론트 |
|---|---|---|
| D-11 (8/18) | API 3개 + Railway 배포 | 목 데이터로 3화면 + Vercel 배포 |
| D-10 (8/19) | 실제 연결 확인, CORS | 실제 API 연결 |
| D-9~8 | 펌웨어 파서 → 차별 규칙 5개 | 발견 카드 다듬기, 접기/펼치기 |
| D-7~6 | 데이터시트 파이프라인 | "해제됨" 표현, 근거 링크 |
| D-5 | 검증 데이터셋 스크립트 | 반응형·접근성 마무리 |

**8/18 밤까지 양쪽 URL이 살아 있어야 한다.** 심사기준 3번이 실제 구동과 배포를 본다.
