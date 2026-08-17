# Prefab API 계약

**이 파일은 `prefab-api`와 `prefab-web` 양쪽에 동일한 내용으로 존재한다.**
바뀌면 양쪽 담당이 함께 고친다. 한쪽이 임의로 필드를 추가하지 않는다.

---

## 엔드포인트

```
POST   /api/v1/checks          검사 생성 (multipart)
GET    /api/v1/checks/{id}     결과 조회
GET    /api/v1/rules           규칙 카탈로그
GET    /healthz                헬스체크
```

---

## POST /api/v1/checks

`multipart/form-data`

| 필드 | 필수 | 설명 |
|---|---|---|
| `netlist` | ✅ | IPC-D-356 파일 (`.d356` / `.ipc` / `.txt`) |
| `bom` | ✕ | 부품 목록 CSV (`refdes, mpn, manufacturer, value`) |
| `firmware` | ✕ | 펌웨어 소스 zip |

- 파일당 10MB 제한, 확장자 검증
- `netlist`가 없으면 `422`

**응답 `201`**
```json
{ "check_id": "chk_7f3a2b", "status": "running" }
```

---

## GET /api/v1/checks/{id}

없으면 `404`.

> 규칙이 더 구현된 뒤의 응답 예시는 [`examples/check.target-with-firmware.json`](./examples/check.target-with-firmware.json)
> 에 있다. **실제 결과가 아니라 목표 명세다.**

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
    "critical": 1,
    "warning": 1,
    "cleared": 1,
    "rules_run": 2,
    "rules_skipped": 10,
    "parts_identified": 0,
    "parts_total": 10
  },
  "pipeline": [
    { "step": 1, "name": "넷리스트 파싱",    "status": "done",    "detail": "네트 8 · 부품 10" },
    { "step": 2, "name": "부품 식별",        "status": "partial", "detail": "BOM 없음 · 좌표 클러스터링만" },
    { "step": 3, "name": "펌웨어 정적 분석", "status": "skipped", "detail": "펌웨어 미제출" },
    { "step": 4, "name": "데이터시트 수집",  "status": "skipped", "detail": "BOM 없음" },
    { "step": 5, "name": "전기적 사실 추출", "status": "skipped", "detail": "데이터시트 없음" },
    { "step": 6, "name": "규칙 엔진",        "status": "done",    "detail": "12개 중 2개 실행" },
    { "step": 7, "name": "리포트 생성",      "status": "done",    "detail": null }
  ],
  "findings": [ /* 아래 형식 */ ],
  "netlist": {
    "nets": [
      { "name": "PRESENCE_3V3", "vias": 2,
        "connections": [ { "ref": "U1", "pin": "LP-G" }, { "ref": "U2", "pin": "OUT" } ] }
    ],
    "parts": [
      { "ref": "U2", "pins": ["GND", "OUT", "UART", "VCC"], "mpn": null }
    ]
  }
}
```

- `status`: `running` | `done` | `failed`
- `pipeline[].status`: `done` | `partial` | `skipped` | `failed`

> ### `skipped`를 숨기지 않는다
> 무엇을 못 했는지 보이는 것이 이 제품의 신뢰다.
> 규칙을 못 돌렸는데 "이상 없음"처럼 보이는 응답은 만들지 않는다.
> 프론트에서도 흐리게 처리하거나 접어서 감추지 않는다.

---

## finding 객체

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
    {
      "kind": "netlist",
      "text": "U2.VCC → 5V_BUS\nU2.OUT → PRESENCE_3V3\nU1.LP-G → PRESENCE_3V3",
      "highlight": ["5V_BUS"]
    },
    {
      "kind": "firmware",
      "file": "src/main.cpp",
      "line": 44,
      "snippet": "pinMode(PRESENCE_PIN, INPUT);",
      "highlight": ["PRESENCE_PIN"]
    },
    {
      "kind": "datasheet",
      "mpn": "HLK-LD2410C",
      "table": "Electrical Characteristics",
      "page": 3,
      "quote": "OUT high level output voltage 3.3V"
    }
  ],
  "suggestion": "U2의 부품번호를 제출하면 데이터시트로 안전 여부를 판정합니다.",
  "unresolved_reason": "U2 미식별 — BOM 필요"
}
```

| 필드 | 값 |
|---|---|
| `severity` | `CRITICAL` \| `WARNING` \| `INFO` |
| `verdict` | `FAIL` \| `PASS` \| `UNRESOLVED` |
| `tier` | `기본` \| `차별` |
| `evidence[].kind` | `netlist` \| `firmware` \| `datasheet` |
| `evidence[].line` | `firmware` 근거의 줄 번호. **부재가 근거면 `null`** (아래) |
| `unresolved_reason` | 없으면 `null` |

> ### 부재도 근거다 — `firmware` 근거의 `line: null`
> R8("회로도에 연결됐는데 코드가 초기화 안 함")은 **코드를 다 읽었고 그 핀이 없다**는 판정이다.
> 가리킬 줄이 없으므로 `line`을 `null`로 두고, `snippet`에 무엇을 읽었고 무엇이 없었는지 적는다.
> 화면은 이때 `파일명 : 줄` 대신 파일명만 표시한다.
>
> ```json
> { "kind": "firmware", "file": "smart_shoe_cabinet_v1.ino", "line": null,
>   "snippet": "검사한 파일 1개 · 106줄 · 참조한 핀 3개 (D2 · D3 · D10)\nD5 는 어느 파일에도 나오지 않습니다.",
>   "highlight": ["D5"] }
> ```
>
> **없는 줄 번호를 지어내지 않는다.** `line: 1` 같은 값을 채우면 사용자가 그 줄을 열어본다.

- 값이 없으면 `null`. 빈 문자열이나 `"N/A"`로 채우지 않는다.
- `highlight`는 프론트에서 강조 표시할 토큰 목록.

---

## GET /api/v1/rules

```json
{
  "rules": [
    { "id": "R11", "title": "네트명이 주장하는 전압 ≠ 소스 부품 전원 도메인",
      "tier": "기본", "severity": "WARNING",
      "needs": ["netlist"], "implemented": true },
    { "id": "R07", "title": "코드가 쓰는 핀이 회로도에 미연결",
      "tier": "차별", "severity": "CRITICAL",
      "needs": ["netlist", "firmware"], "implemented": false }
  ]
}
```

**미구현 규칙도 `implemented: false`로 포함한다.** 숨기지 않는다.

---

## 오류 응답

```json
{ "error": { "code": "NETLIST_REQUIRED", "message": "넷리스트 파일이 필요합니다." } }
```

| 상황 | 코드 | 상태 |
|---|---|---|
| 넷리스트 없음 | `NETLIST_REQUIRED` | 422 |
| 파싱 실패 | `NETLIST_PARSE_FAILED` | 422 |
| 파일 크기 초과 | `FILE_TOO_LARGE` | 413 |
| check_id 없음 | `CHECK_NOT_FOUND` | 404 |

메시지는 **무엇이 잘못됐고 어떻게 고치는지** 알려준다. 사과하지 않는다.

---

## 디자인 토큰 (프론트 공유)

토스 계열 톤. 색은 역할 이름으로 부른다.
값의 진실은 `apps/web/tailwind.config.js` 하나다 — 여기는 사본이다.

```
bg          #F7F8FA    페이지 바탕
surface     #FFFFFF    카드 · 시트
surface-2   #F2F4F6    카드 안에서 한 단 낮은 면 (코드 발췌 · 칩)
ink         #191F28    본문
sub         #4E5968    보조 텍스트
mute        #8B95A1    더 흐린 텍스트 · 비활성
line        #E5E8EB    경계선

brand        #3182F6   강조
brand-strong #1B64DA   버튼 · 링크
crit  #D6293E / crit-weak  #FEECEE    CRITICAL
warn  #B45309 / warn-weak  #FFF4E5    WARNING · skipped
ok    #087A57 / ok-weak    #E6F7F1    PASS · cleared · done

font-sans   'Pretendard'
font-mono   'JetBrains Mono'    넷리스트 · 코드 · 핀 이름 · 규칙 ID
```

`highlight` 토큰은 `crit-weak` 배경 + `crit` 굵은 글자로 강조한다.

## CORS

배포는 후순위지만 **CORS는 지금 넣어둔다.** 나중에 붙일 때 반나절이 날아간다.

```
허용 origin: http://localhost:5173, <배포 URL — 정해지면 추가>
허용 method: GET, POST, OPTIONS
```

업로드가 `multipart/form-data`라 프리플라이트(OPTIONS)가 먼저 날아간다.
