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
| `unresolved_reason` | 없으면 `null` |

- 값이 없으면 `null`. 빈 문자열이나 `"N/A"`로 채우지 않는다.
- `highlight`는 프론트에서 redpen 밑줄로 강조할 토큰 목록.

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
font-cond   'IBM Plex Sans Condensed'   라벨 · 대문자 · letter-spacing .16em
font-mono   'IBM Plex Mono'             넷리스트 · 코드 · 핀 이름 · 규칙 ID
```

---

## CORS

백엔드 첫 커밋에 포함한다. 배포 직전에 발견하면 반나절이 날아간다.

```
허용 origin: <Vercel 배포 URL>, http://localhost:5173
```
