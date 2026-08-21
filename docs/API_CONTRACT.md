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
| `netlist` | ✅ | IPC-D-356 (`.d356` / `.ipc` / `.txt`) 또는 KiCad 회로도 넷리스트 kicadxml (`.xml` / `.net`). **형식은 내용으로 가른다** |
| `bom` | ✕ | 부품 목록 CSV (`refdes, mpn, manufacturer, value`) |
| `firmware` | ✕ | 펌웨어 소스 zip |
| `previous_netlist` | ✕ | **바뀌기 전** 회로도. 같은 형식들을 받는다 |

- 파일당 10MB 제한, 확장자 검증
- `netlist`가 없으면 `422`

### `previous_netlist` — R10(드리프트)이 이걸로만 돈다

이 제품의 이름이 붙은 규칙이 R10 이다. **한 장만 보면 "D2 가 안 붙었다"와
"D4 를 코드가 안 쓴다"까지가 전부이고, 둘이 같은 사건인지는 이전 상태를 알아야
말할 수 있다.**

```
이전   PRESENCE_3V3 → U1.D2      코드: pinMode(D2, ...)
지금   PRESENCE_3V3 → U1.D4      코드: 그대로 D2
       ↑ 회로도가 옮겼고 코드는 안 따라왔다
```

**안 주면 실패가 아니다.** R10 이 조용하고, `pipeline` 의 「규칙 엔진」 단계가
*"R10(드리프트)은 이전 회로도가 없어 비교할 대상이 없었습니다"* 라고 적는다.
`rules_run` 은 그대로 12 다 — 규칙은 돌았고 볼 것이 없었을 뿐이며,
**그 사실을 숨기지 않는 것**으로 처리한다.

**주고서 못 읽으면 그건 실패다.** `PREVIOUS_NETLIST_PARSE_FAILED` (422).
조용히 버리면 사용자가 "드리프트 없음" 으로 읽는데, 실제로는 비교를 안 한 것이다.
오류 문구가 지금 넷리스트 오류와 구분된다 — 둘 다 넷리스트라 어느 파일을
고쳐야 할지 말해 주지 않으면 멀쩡한 파일을 뜯어보게 된다.

**형식이 같을 필요는 없다.** 예전에는 IPC-D-356 으로 뽑고 지금은 회로도
넷리스트로 뽑는 경우가 실제로 생긴다.

**응답 `201`**
```json
{ "check_id": "chk_7f3a2b", "status": "done" }
```

> ### 검사는 동기로 끝난다 — 지금은 `running` 이 나오지 않는다
> 규칙 2개가 순수 함수이고 입력이 네트 8 · 부품 10 규모라 검사가 밀리초 안에 끝난다.
> 그래서 POST 응답이 이미 `"status": "done"` 이다. 큐를 쓰지 않는다.
>
> 프론트는 `/c/{id}` 로 보내도 되고(첫 폴링에서 바로 `/r/{id}` 로 넘어간다)
> 곧장 `/r/{id}` 로 가도 된다. 화면 코드를 고칠 필요는 없다.
>
> 펌웨어 정적 분석이 붙어 검사가 5초를 넘기기 시작하면 `BackgroundTasks` 로 바꾸고
> 그때 `running` + 부분 `pipeline` 을 채운다. **바뀌면 이 절을 먼저 고친다.**

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
    /* BOM 을 냈으면      { "filename": "bom.csv", "parts": 10 } */
    /* 펌웨어를 냈으면    { "filename": "src.zip", "files": 1 } */
  },
  "summary": {
    "critical": 1,
    "warning": 1,
    "info": 0,
    "cleared": 1,
    "rules_run": 2,
    "rules_skipped": 9,
    "rules_total": 11,
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
        "connections": [
          { "ref": "U1", "pin": "LP-G", "silk": "D2", "gpio": 2 },
          { "ref": "U2", "pin": "OUT" }
        ] }
    ],
    "parts": [
      { "ref": "U2", "pins": ["GND", "OUT", "UART", "VCC"], "mpn": null },
      { "ref": "U1", "pins": ["3V3", "5V", "LP-G", "SDIO", "..."], "mpn": null,
        "pads": [ { "pin": "LP-G", "silk": "D2", "gpio": 2 },
                  { "pin": "SDIO", "silk": "D5", "gpio": 23 } ] }
    ]
  }
}
```

- `status`: `running` | `done` | `failed`
- `pipeline[].status`: `done` | `partial` | `skipped` | `failed`
- `created_at`: **UTC** (`Z` 로 끝난다). 서버는 시간대를 정하지 않는다.
  한국 시간 표시는 화면이 변환한다.
- `summary.critical + warning + info + cleared` 는 **`findings` 개수와 항상 같다.**
  심각도는 세 단계이고 `info` 도 센다 — 안 세면 화면의 타일 합이 발견 수보다 작아진다.
- `summary.rules_run + summary.rules_skipped == summary.rules_total` 이 **항상 성립한다.**
  세 값 모두 규칙 레지스트리에서 계산된다. 문서에 손으로 적은 숫자를 쓰지 않는다.
  현재 `rules_total` 은 11 이다 (R6 은 폐기). 구현된 것은 **R07 · R08 · R11 · R12** 네 개다.
- `pipeline[].detail` 문구는 **계약이 아니다.** 화면에 그대로 찍기만 하고 파싱하지 않는다.
- `summary.parts_identified` 는 **BOM 에서 부품번호까지 확인된 부품 수**다.
  BOM 을 안 내면 0 이다. 부품번호가 빈 행(수동 소자 등)은 세지 않는다.
- `parts[].mpn` 은 BOM 이 있을 때만 채워진다. 없으면 `null` 이다.

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
| `evidence[].page` | `datasheet` 근거의 쪽 번호. **실측이 근거면 `null`** (아래) |
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

> ### 실측도 근거다 — `datasheet` 근거의 `page: null`
> 데이터시트가 없거나 그 항목을 안 싣는 부품이 있다. 그때 남는 길이 **실물을 재는 것**이다.
> 측정도 출처지만 쪽 번호가 없다. `page` 를 비우고 `table` 에 무엇을 어떻게 쟀는지,
> `quote` 에 측정 기록을 그대로 적는다. 화면은 이때 `표 · p.N` 대신 `표`만 표시한다.
>
> ```json
> { "kind": "datasheet", "mpn": "JQC-3FF-S-Z", "page": null,
>   "table": "IN↔VCC 저항 측정 (2026-08-19 · 한지양)",
>   "quote": "20kΩ 및 2MΩ 범위로 측정했는데 모두 OL(1.)이 나왔습니다." }
> ```
>
> **없는 쪽 번호를 지어내지 않는다.** `page: 0` 을 넣으면 화면에 `p.0` 이 뜬다.

- 값이 없으면 `null`. 빈 문자열이나 `"N/A"`로 채우지 않는다.
- `highlight`는 프론트에서 강조 표시할 토큰 목록.
- `evidence` 객체는 `kind` 에 해당하는 키만 담는다. 다른 kind 의 키를 `null` 로 채우지 않는다.
- `kind: "firmware"` 의 `file` 은 **업로드한 zip 내부의 상대 경로**다.
  절대 경로나 서버 임시 디렉터리 경로가 섞여 나가지 않는다.

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
      "needs": ["netlist", "firmware"], "implemented": true },
    { "id": "R04", "title": "외부 부품 출력이 GPIO 입력 최대 정격 초과",
      "tier": "기본", "severity": "CRITICAL",
      "needs": ["netlist", "bom"], "implemented": false }
  ]
}
```

**미구현 규칙도 `implemented: false`로 포함한다.** 숨기지 않는다.

`id` 는 **세 자리 고정**이다 (`R01` … `R12`). `R06`(I2C 풀업 누락)은 폐기했고 번호를 재사용하지 않는다.
`needs` 어휘는 `netlist` | `bom` | `firmware` 세 개뿐이다.

목 모드용 응답 예시는 `apps/web/src/mocks/rules.json` 에 있다. 다음 명령으로 다시 뽑는다.

```bash
cd apps/api && python -m prefab --rules-json > ../web/src/mocks/rules.json
```

---

## 핀 신원 — `silk` · `gpio` (선택 필드)

IPC-D-356 은 핀 이름을 **4자에서 자른다.** 그래서 물리적으로 다른 핀이 같은 이름으로 뭉친다.
우리 보드 U1 은 레코드 25개인데 이름 종류는 18개다 (`LP-G` ×3 · `SDIO` ×3).
`pin` 만 봐서는 `_IN_ACTIVE_LOW` 에 붙은 `U1.SDIO` 가 D3 인지 D4 인지 D5 인지 알 수 없다.

**좌표로 푼다.** 헤더 열을 X 로 묶고 Y 내림차순으로 읽은 이름 나열이 모듈 표의 서명과
전부 일치할 때만 라벨을 붙인다. 한 열만 맞고 나머지가 어긋나면 다른 보드이므로
**아무것도 붙이지 않는다.** 절반만 믿으면 그 위에 세운 R07·R08 이 통째로 거짓말이 된다.

| 필드 | 위치 | 값 |
|---|---|---|
| `silk` | `connections[]` · `parts[].pads[]` | 보드 실크 라벨 (`D5`) |
| `gpio` | 같음 | 칩 GPIO 번호 (`23`). 전원·접지 헤더 핀에는 없다 |
| `pads` | `parts[]` | 이름이 뭉치기 전의 패드 목록. 확정된 패드만 실린다 |

- **전부 선택 필드다.** 없으면 화면은 지금처럼 `pin` 만 쓰면 된다. 깨지지 않는다.
- `pins` 는 그대로 둔다. 기존 필드를 바꾸지 않는다.
- 모듈을 못 알아본 부품에는 `pads` 가 아예 없다. 빈 배열을 넣지 않는다.
- 발견의 `evidence.text` 도 확정된 패드는 **실크 라벨로 적는다** (`U1.SDIO` → `U1.D5`).
  잘린 원본 이름은 괄호로 함께 남긴다.

표의 진실은 [`CHIPS.md`](./CHIPS.md) 「모듈 핀아웃」 절이고, 코드 사본은
`apps/api/src/prefab/chips/__init__.py` 다. 하드웨어 담당 실물 대조 대기 중이다.

---

## 오류 응답

```json
{ "error": { "code": "NETLIST_REQUIRED", "message": "넷리스트 파일이 필요합니다." } }
```

| 상황 | 코드 | 상태 |
|---|---|---|
| 넷리스트 없음 | `NETLIST_REQUIRED` | 422 |
| 파싱 실패 | `NETLIST_PARSE_FAILED` | 422 |
| **이전** 회로도만 못 읽음 | `PREVIOUS_NETLIST_PARSE_FAILED` | 422 |
| BOM 을 읽지 못함 | `BOM_PARSE_FAILED` | 422 |
| 파일 크기 초과 (10MB) | `FILE_TOO_LARGE` | 413 |
| 확장자 불일치 | `UNSUPPORTED_FILE_TYPE` | 415 |
| 펌웨어 zip 을 못 읽음 | `FIRMWARE_UNREADABLE` | 422 |
| BOM CSV 를 못 읽음 | `BOM_PARSE_FAILED` | 422 |
| check_id 없음 | `CHECK_NOT_FOUND` | 404 |
| 서버가 처리 못 한 오류 | `INTERNAL_ERROR` | 500 |

메시지는 **무엇이 잘못됐고 어떻게 고치는지** 알려준다. 사과하지 않는다.
프론트는 `error.message` 를 그대로 노출한다. 서버가 스택트레이스를 message 에 넣지 않는다.

받는 확장자: `netlist` = `.d356` / `.ipc` / `.txt` / `.xml` / `.net` · `bom` = `.csv` · `firmware` = `.zip`

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

## 로컬에서 붙이기

배포는 후순위다. 로컬끼리 붙이는 데는 아무 준비물이 없다 — API 키도 DB 설치도 없다.

```bash
# 백엔드 (기본 포트 8000)
cd apps/api && uvicorn web.app:app --reload --port 8000

# 프론트
cd apps/web && echo "VITE_API_BASE=http://localhost:8000" > .env && pnpm dev
```

`ALLOWED_ORIGINS` 를 안 넣으면 `localhost:5173` · `127.0.0.1:5173` 이 기본으로 허용된다.
SQLite 파일(`prefab.db`)은 첫 실행에 자동 생성된다.

붙었는지 확인:

```bash
cd apps/api && ./scripts/smoke.sh http://localhost:8000
```

헬스체크 → 규칙 카탈로그 → CORS 프리플라이트 → 실제 보드 업로드 → 골든 3건 일치까지
순서대로 보고, 하나라도 어긋나면 0이 아닌 코드로 끝난다.

## CORS

배포는 후순위지만 **CORS는 지금 넣어둔다.** 나중에 붙일 때 반나절이 날아간다. — **넣었다.**

```
허용 origin : http://localhost:5173, http://127.0.0.1:5173
              + https://*.vercel.app (프리뷰 배포는 URL 이 매번 바뀐다)
              + <배포 URL — 정해지면 ALLOWED_ORIGINS 에 추가>
허용 method : GET, POST, OPTIONS
허용 header : *
```

업로드가 `multipart/form-data`라 **프리플라이트(OPTIONS)가 먼저 날아간다.**
GET 만 열어두면 로컬에서 붙일 때부터 업로드가 통째로 막힌다.

배포 origin 은 환경변수로 넣는다. 코드에 하드코딩하지 않는다.

```
ALLOWED_ORIGINS=https://<배포-URL>,http://localhost:5173
```
