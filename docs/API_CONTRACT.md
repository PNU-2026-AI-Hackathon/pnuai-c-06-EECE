# Prefab API 계약

**이 파일은 `prefab-api`와 `prefab-web` 양쪽에 동일한 내용으로 존재한다.**
바뀌면 양쪽 담당이 함께 고친다. 한쪽이 임의로 필드를 추가하지 않는다.

---

## 엔드포인트

```
POST   /api/v1/checks          검사 생성 (multipart)
GET    /api/v1/checks/{id}     결과 조회
GET    /api/v1/rules           규칙 카탈로그
POST   /api/v1/waitlist        출시 알림 대기 명단
GET    /healthz                헬스체크
```

---

## POST /api/v1/checks

> **로그인이 필요하다** (8/24 팀장 결정). 세션 쿠키가 없으면 `401 LOGIN_REQUIRED`.
> 결과를 *보는* 것은 그대로 열려 있다 — 그 선이 로그인 벽의 범위다.


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

> **로그인이 필요 없다.** 주소를 아는 사람은 연다 — 그게 기본 공유 방식이다.
> 접근 통제는 **ID 를 못 맞히는 것**이 전부다 (16바이트 · 32자리).
>
> **주인이 비공개로 바꾼 검사는 예외다.** 그때는 주인만 200 이고 나머지는 404 다.
> 비공개는 **무료 기능**이다 — 보안을 요금제 뒤에 두면 돈을 안 내는 사람의
> 회로도를 인질로 잡는 셈이 된다.
>
> **403 이 아니라 404 로 돌려준다.** 403 은 "여기 뭔가 있다"를 알려주는데,
> ID 를 못 맞히는 것이 접근 통제의 전부라 존재 자체를 안 알리는 편이 맞다.

응답에 두 가지가 더 실린다.

- `visibility` — `"link"`(주소를 아는 누구나) 또는 `"private"`(주인만)
- `owned` — 지금 보는 사람이 이 검사의 주인인가. **화면이 공개 범위 전환 버튼을
  누구에게 보일지 정하는 데 쓴다.** 보는 사람은 이미 이 검사를 열었으므로 새로 새는 정보가 없다.

**payload 안이 아니라 별도 칼럼에서 온다.** payload 는 검사한 순간의 판정 기록이고,
공개 범위는 주인이 언제든 바꾸는 값이라 섞으면 안 된다.

## POST /api/v1/checks/{id}/visibility

**주인만.** 아니면 404 (남의 검사의 존재를 알려주지 않는다).

```json
{ "visibility": "private" }
```

돌려주는 것 — `{ "check_id": "chk_...", "visibility": "private" }`


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

## POST /api/v1/waitlist

**결제를 만들기 전에 살 사람이 있는지 재는 자리다.** 요금표가 「준비 중」이라고만
적혀 있는 동안은 방문자가 반응할 대상이 없어서, 가격이 비싼지 싼지도 알 수 없다.

```json
{ "email": "you@example.com", "plan": "pro" }
```

- `plan` 은 `"pro"` 또는 `"team"` 뿐이다. **다른 값은 400 으로 거절한다** —
  프론트가 오타를 내면 조용히 저장되고 나중에 집계가 틀린다
- 이메일은 앞뒤 공백을 떼고 소문자로 저장한다. `Me@Example.COM` 과
  `me@example.com` 을 **두 명으로 세면 수요를 부풀려 읽는다**
- 같은 (이메일, 요금제)를 다시 보내도 **201 이다.** "이미 등록하셨습니다" 는
  사용자에게 쓸모가 없고, 그 주소가 명단에 있다는 사실을 아무에게나 알려주는 셈이다

성공 응답 — **인원 수를 돌려주지 않는다.** 화면에 "3명 대기 중" 이 뜨면
오히려 안 팔리는 제품처럼 보인다.

```json
{ "joined": true }
```

거절 코드: `EMAIL_REQUIRED` · `EMAIL_INVALID` · `EMAIL_TOO_LONG` · `PLAN_UNKNOWN` · `BAD_REQUEST`

검사·인증과 같은 요청 제한을 받는다.

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

## `discovery` — 선택 필드. **판정이 아니다**

검사 응답에 이 키가 **있을 수도 있다.** 없으면 발견 루프를 안 돌린 것이다.

```json
{
  "discovery": {
    "candidates": [
      {
        "title": "pinMode(OUTPUT)가 안전값 출력보다 먼저라서 리셋마다 릴레이가 순간 ON",
        "why": "…",
        "citations": [
          { "kind": "firmware", "where": "presence_light.ino", "what": "13",
            "quote": "pinMode(RELAY_PIN, OUTPUT);" }
        ],
        "covered_by": null
      }
    ],
    "dropped": [{ "title": "…", "reason": "인용한 내용이 없습니다" }],
    "unavailable": null,
    "notes": ["모델이 3건을 냈고 코드가 1건을 남겼습니다."]
  }
}
```

**`findings` 와 섞지 않는다.** 후보에는 `severity` 도 `verdict` 도 **없다** —
붙이면 화면에서 발견처럼 보인다. 프론트는 다른 섹션·다른 색으로 그린다.

**`dropped` 를 같이 싣는다.** 몇 개를 왜 버렸는지 안 보이면 "두 개 찾았습니다" 가
"두 개만 말했습니다" 로 읽힌다. `unavailable` 은 **모델을 못 불렀을 때만** 찬다 —
부르지 않은 것과 못 부른 것은 다르다.

---

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


---

## API 키

**웹 화면 없이 검사를 돌리는 길이다.** CI 러너에는 브라우저가 없고 쿠키도 없다.

```
Authorization: Bearer prefab_<64자리 16진수>
```

키를 주면 세션 쿠키보다 **먼저** 본다. 쿼리스트링으로는 안 받는다 —
주소는 서버 로그·브라우저 기록·리퍼러에 그대로 남는다.

### GET /api/v1/keys

```json
{ "keys": [{ "id": "...", "label": "CI 러너", "created_at": "...", "last_used_at": "..." }],
  "max": 5 }
```

**원문은 여기 없다.** DB 에도 SHA-256 만 남는다 (세션 토큰과 같은 규칙).

### POST /api/v1/keys

`{ "label": "CI 러너" }` → 만든 키 + **`token`**.

**`token` 은 이 응답에만 실린다.** 다시는 못 본다. 잃어버리면 새로 만들어야 한다.

### DELETE /api/v1/keys/{id}

남의 키는 `404`. 지운 키는 **즉시** 안 먹는다.

---

## GitHub 으로 로그인

**브라우저가 주소창으로 오는 자리다. `fetch` 가 아니다.** OAuth 는 사용자를
GitHub 으로 실제로 보냈다가 데려오는 흐름이라 XHR 로는 성립하지 않는다.
화면은 `<a href>` 로 건다.

```
GET /api/v1/auth/github/start?next=/mine    → 302 GitHub 승인 화면
GET /api/v1/auth/github/callback            → 302 화면 (세션 쿠키가 여기서 심긴다)
```

### 켜졌는지 화면이 아는 법

`GET /api/v1/auth/me` 에 실린다.

```json
{ "user": null, "storage": { ... }, "github": { "enabled": false } }
```

**`enabled` 가 거짓이면 화면은 버튼을 아예 안 그린다.** 서버에 GitHub 앱이
설정되지 않으면 `/start` 가 `404` 다 — 눌러도 안 되는 버튼을 두지 않는다 (헌법 2-4).

### 실패하면 화면으로 사유를 달아 되돌린다

```
{WEB_APP_URL}/login?error=<코드>
```

| 코드 | 뜻 |
|---|---|
| `cancelled` | 사용자가 GitHub 화면에서 취소했다. **오류가 아니다** |
| `no_verified_email` | GitHub 계정에 **인증된** 이메일이 없다 |
| `bad_state` | 우리가 시작한 흐름이 아니거나 시간이 지났다 (CSRF 방어) |
| `exchange_failed` · `github_unreachable` | GitHub 과의 통신이 안 됐다 |

`next` 는 **목록에 있는 경로만** 받는다 (`/mine` · `/check` · `/pricing` · `/`).
그 밖은 `/mine` 으로 간다 — 우리 로그인 링크가 남의 사이트로 떨어뜨리는
미끼가 되면 안 된다 (오픈 리다이렉트).

### 서버 환경변수

```
GITHUB_CLIENT_ID        GitHub OAuth 앱의 Client ID
GITHUB_CLIENT_SECRET    Client secret. **state 서명 열쇠로도 쓴다**
GITHUB_REDIRECT_URI     {API 주소}/api/v1/auth/github/callback
WEB_APP_URL             다 끝나고 사람을 보낼 화면 주소
```

넷 중 하나라도 비면 기능이 통째로 꺼진다.

---

## 저장소 연동

CI 설정의 네 단계 중 **경로 맞추기**를 대신한다. 저장소를 훑어 넷리스트·펌웨어·
부품목록을 찾고, 경로가 채워진 워크플로 파일을 **PR 로** 올린다.

```
GET  /api/v1/github/connect/start   → 302 GitHub (scope: repo workflow)
GET  /api/v1/github/repos           → 쓸 수 있는 저장소 (push 권한 있는 것만)
GET  /api/v1/github/scan?repo=&branch=  → 파일 후보
POST /api/v1/github/setup           → PR 을 연다
```

### 접근 토큰을 저장하지 않는다

연동은 한 번 하는 일이라, 권한을 받아 **그 흐름 안에서만 쓰고 버린다.**
짧게 사는 httpOnly 쿠키(`prefab_gh_connect`, 15분)로 나른다.

저장하면 우리 DB 가 남의 **비공개 회로도 저장소 열쇠**를 들고 있게 되는데,
지금 우리에게는 그걸 지킬 암호화도 살아남는 저장소도 없다.
`tests/test_repo_connect.py` 가 DB 전체를 훑어 토큰이 안 들어갔는지 확인한다.

### 권한을 로그인과 나눈다

```
로그인   read:user user:email      이름과 이메일만
연동     repo workflow             저장소를 훑고 워크플로 파일을 넣는다
```

로그인하려고 눌렀는데 "모든 저장소를 읽고 씁니다" 가 뜨면 거기서 그만둔다.
연동을 누른 사람은 무엇을 하려는지 알고 누른 것이라 그때 물어보면 납득이 된다.

`workflow` 가 따로 필요하다 — `repo` 만으로는 `.github/workflows/` 아래 파일을
못 만든다. GitHub 이 그 폴더만 별도로 잠가 뒀다.

### `scan` 응답 — **고르지 않는다. 후보를 근거와 함께 늘어놓는다**

```json
{ "repo": "me/board", "branch": "main", "files_seen": 42, "truncated": false,
  "netlist": {
    "picked": null,
    "candidates": [
      { "path": "pcb/rev1/board.d356", "score": 1.0,
        "reason": "IPC-D-356 전용 확장자입니다 · pcb/ 아래에 있습니다" },
      { "path": "pcb/rev2/board.d356", "score": 1.0, "reason": "…" }
    ]
  },
  "firmware": { "picked": "src", "candidates": [ … ] },
  "bom": { "picked": null, "candidates": [] } }
```

**`picked: null` 은 「없다」가 아니라 「우리가 고를 만큼 확신이 없다」이다.**
화면은 그때 칸을 비워 두고 사용자가 고르게 한다. 틀린 값을 채워 두면 검토를
건너뛰게 되고, 액션이 "넷리스트를 못 찾았습니다" 로 죽는다 — 사용자는 우리
도구가 고장 났다고 읽는다 (헌법 2-3).

안 고르는 두 경우 — **① 1등 점수가 0.7 미만 ② 1등과 2등이 0.1 이내로 붙음.**

`truncated` 가 참이면 저장소가 커서 다 못 본 것이다. **이걸 숨기면
「넷리스트가 없습니다」가 거짓이 된다** (헌법 2-2).

### `setup` — 기본 브랜치에 직접 안 쓴다

`prefab/ci-설정` 브랜치를 만들어 PR 로 올린다. 곧바로 커밋하면 마음에 안 들어도
이미 들어간 뒤다. **되돌릴 수 있는 형태로 준다.**

**시크릿은 우리가 안 넣는다.** 넣으려면 저장소의 모든 비밀값을 바꿀 수 있는
권한을 받아야 한다. 그 권한은 안 받고, PR 설명에 직접 넣는 법을 적는다.
