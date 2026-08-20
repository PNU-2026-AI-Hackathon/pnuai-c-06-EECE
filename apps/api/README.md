# Prefab API

**이미 짜놓은 펌웨어가 바뀐 회로도를 따라가고 있는지 검사합니다. 보드를 발주하기 전에요.**

회로도(넷리스트) · 펌웨어 소스 · 부품 데이터시트를 함께 읽고, 셋 사이의 어긋남을 찾습니다.

---

## 왜 필요한가

임베디드에서 가장 비싼 버그는 **컴파일도 되고 업로드도 되는 버그**입니다.

- 코드는 정상 컴파일 → 컴파일러가 못 잡음
- 회로도는 DRC 통과 → EDA 툴이 못 잡음
- 문제는 **둘 사이**에 있음 → 아무 도구도 안 봄
- 발견 시점: 보드가 도착해서 안 켜질 때

업계 조사로는 프로젝트당 평균 2.9회의 리스핀이 발생하고, 회당 일정 영향이 8.5일입니다
([Lifecycle Insights](https://www.cadstrom.io/resources/the-hidden-cost-of-pcb-respins-why-90-of-first-prototypes-fail)).
소규모 보드라도 재발주 한 번에 2~4주가 사라집니다.

### 기존 도구와의 관계

| 도구 | 회로도 | 기존 펌웨어 검증 | 실물 보드 |
|---|---|---|---|
| STM32CubeMX, esp32pin.com | 규칙 표만 제공 | ✕ | 불필요 |
| Traceformer, Flux Design Review | ✅ 데이터시트까지 | **✕ 명시적 제외** | 불필요 |
| Embedder | 코드 생성 입력용 | ✕ (생성이지 검증 아님) | **필요** |
| **Prefab** | ✅ | **✅** | 불필요 |

회로도만 보는 도구는 이미 있습니다. **코드까지 함께 보는 도구가 없습니다.**

---

## 설계 원칙

> **토폴로지가 질문을 던지고, 데이터시트가 답한다.**

결정적 코드가 플래그를 세우고, LLM은 그 플래그를 **지우기 위해서만** 호출됩니다.

- LLM 출력은 JSON 스키마로 강제 — 자유 텍스트 판정 없음
- 판정 함수는 순수 함수 — 같은 입력이면 항상 같은 결과
- 모든 판정에 근거 위치가 붙음 (파일:라인 / 데이터시트 페이지·표)
- 모르면 `UNRESOLVED` — 추측해서 통과시키지 않음

---

## 현재 상태

숨기지 않고 그대로 적습니다.

| 구성요소 | 상태 |
|---|---|
| IPC-D-356 넷리스트 파서 | ✅ 동작 (실제 보드 검증) |
| 규칙 엔진 | ✅ 동작 |
| 구현된 규칙 | **10 / 11** (차별 4 · 기본 6) — 남은 하나는 R10(드리프트) |
| REST API (4개 엔드포인트 + CORS) | ✅ 동작 |
| CLI (`python -m prefab`) | ✅ 동작 |
| 펌웨어 정적 분석 | ✅ 동작 (핀 사용·방향·상수 추적) |
| 모듈 핀아웃 DB | **1 모듈** (XIAO ESP32-C6 · 하드웨어 담당 확정 완료) |
| BOM CSV 파서 | ✅ 동작 |
| 데이터시트 파이프라인 | ✅ 동작 (PDF → LLM → **원문 대조 검증**) |
| 부품 사실 DB | **2 부품 · 13건** (`parts/*.json`) |
| 검증 측정 | ✅ `python -m prefab --measure` (케이스 24개) |
| GitHub Action (CI) | ✅ pytest · 측정 · 계약 불변식 |
| **커밋 간 드리프트 검사** | ✅ PR 마다 회로도 ↔ 코드 대조 (F-1) |
| 샘플 검사 (업로드 없이) | ✅ `GET /api/v1/checks/chk_sample01` (F-4) |

### 알려진 문제
- **검증 숫자가 회귀 방지다.** 결함 주입 데이터셋은 우리가 만든 것이라 정답을 알지만,
  남의 보드에서의 재현율은 아직 못 잰다 (E-1 오픈소스 커밋 라벨링 미착수).
  `--measure` 보고서가 그 한계를 직접 출력한다.
- **ESP32-C6 의 부팅 시 출력 핀 목록이 GPIO16 하나뿐이다.** 없어서가 아니라
  Espressif 공식 문서에서 못 찾아서다. R09 는 표에 없는 핀에 아무 말도 하지 않는다.

---

## 빠른 시작

```bash
cd apps/api
uv sync                     # 또는 pip install -e ".[dev]"
pytest -q
python -m prefab --measure  # 검출율 · 오탐율

# 발견이 0건일 때 — "이상 없음" 인지 "못 봤음" 인지
python -m prefab tests/fixtures/schematic-gpio-named.net.xml --why

# 실제 보드 — 넷리스트만 (치명 2 · 경고 1)
python -m prefab tests/fixtures/esp32-c6-presence-smart-light.d356

# 실제 보드 — 펌웨어까지 (차별 규칙 R07·R08)
python -m prefab tests/fixtures/esp32-c6-presence-smart-light.d356 \
  --firmware tests/fixtures/esp32-c6-presence-smart-light.firmware

# BOM 까지 넣기 (부품번호 식별 → 데이터시트 축의 입구)
python -m prefab tests/fixtures/esp32-c6-presence-smart-light.d356 \
  --bom tests/fixtures/esp32-c6-presence-smart-light.bom.csv \
  --firmware tests/fixtures/esp32-c6-presence-smart-light.firmware

# 프론트 목 데이터 재생성 (요청서 3번)
python -m prefab tests/fixtures/esp32-c6-presence-smart-light.d356 --json \
  > ../web/src/mocks/check.json
python -m prefab --rules-json > ../web/src/mocks/rules.json

# API 서버
ALLOWED_ORIGINS=http://localhost:5173 uvicorn web.app:app --reload --port 8000

# 배포한 URL 확인 (헬스체크 · CORS 프리플라이트 · 업로드 · 골든 결과)
./scripts/smoke.sh https://<배포-URL>
```

## 커밋 간 드리프트 검사

**이것이 제품의 최종 형태입니다.** 회로도를 고치고 코드를 안 고치면, 그 PR 에서 걸립니다.

```bash
python -m prefab board.d356 --firmware fw/ --json > before.json   # 고치기 전
python -m prefab board.d356 --firmware fw/ --json > after.json    # 고친 뒤
python -m prefab --diff before.json after.json --fail-on-new
```

`.github/workflows/drift.yml` 이 PR 마다 이걸 돌리고 결과를 코멘트로 답니다.
새로 생긴 치명 발견이 있으면 빨간불입니다.

**양쪽 다 지금 코드로 돌립니다.** 예전 코드로 예전 입력을 돌리면 규칙을 고친 것과
보드를 고친 것이 섞여서, 규칙을 추가한 PR 이 "보드가 나빠졌다"로 읽힙니다.

실제로 어떻게 보이는지 — 실측 보드에서 센서 OUT 을 D2 → D4 로 옮기고 코드는 그대로 뒀을 때:

```
🔴 새로 생긴 발견
  R07 · U1.D2   코드가 D2(GPIO2) 핀을 출력으로 구동합니다.
                그런데 회로도에서 이 핀은 아무 네트에도 연결돼 있지 않습니다.
  R08 · D4      회로도는 D4(GPIO22)를 PRESENCE_3V3 로 배선해 뒀는데,
                코드에는 이 핀이 한 번도 나오지 않습니다.
```

넷리스트 **두 줄** 차이입니다. 컴파일도 되고 DRC 도 통과합니다.

---

## 배포

```bash
# Railway
railway up                  # apps/api/Dockerfile 을 씀 (railway.json)
railway variables --set ALLOWED_ORIGINS=https://<vercel-url>,http://localhost:5173

# Render 는 저장소 루트의 render.yaml 을 읽는다
```

`ALLOWED_ORIGINS` 를 안 넣으면 localhost 만 허용된다 — **배포된 프론트에서 업로드가 막힌다.**

---

## API

전체 스펙은 [`API_CONTRACT.md`](./API_CONTRACT.md).

```
POST   /api/v1/checks          검사 생성 (multipart: netlist, bom?, firmware?)
GET    /api/v1/checks/{id}     결과 조회
GET    /api/v1/rules           규칙 카탈로그
GET    /healthz
```

### 업로드 없이 결과부터 보기

서버가 켜질 때 실측 보드 결과 하나를 미리 넣어 둡니다. **새 엔드포인트가 아닙니다.**

```bash
curl https://<host>/                              # sample_check 경로를 알려준다
curl https://<host>/api/v1/checks/chk_sample01    # 치명 4 · 경고 1 · R07·R08 포함
```

데모에서 파일 세 개를 골라 올리는 동안 이야기가 죽는 것을 막기 위한 것입니다.

```bash
curl -F "netlist=@board.d356" https://<host>/api/v1/checks
```

응답의 `pipeline` 배열은 **못 한 단계도 그대로 싣습니다.** BOM이 없으면
데이터시트 단계가 `skipped`로 오고 사유가 붙습니다. 규칙을 못 돌렸는데
"이상 없음"처럼 보이는 응답은 만들지 않습니다.

---

## 규칙 카탈로그

`기본` 등급은 기존 상용 도구가 이미 제공하는 범위, `차별`은 Prefab만 하는 것입니다.

**이 표는 사본입니다. 진실은 `src/prefab/catalog.py` 하나입니다.**
살아 있는 목록은 `python -m prefab --rules-json` 또는 `GET /api/v1/rules` 로 보세요.

| ID | 규칙 | 등급 | 필요 입력 | 상태 |
|---|---|---|---|---|
| R01 | 코드가 이 칩에서 쓸 수 없는 핀을 사용 | 차별 | netlist, firmware | ✅ |
| R02 | 회로도가 SPI 플래시 전용 핀에 배선 | 기본 | netlist | ✅ |
| R03 | 스트래핑 핀이 전원·접지에 직결 | 기본 | netlist | ✅ |
| R04 | 외부 부품 출력이 GPIO 입력 최대 정격 초과 | 기본 | netlist, bom | ✅ |
| R05 | 이 칩이 지원하지 않는 주변장치 조합 | 차별 | netlist, firmware | ✅ |
| R07 | 코드가 쓰는 핀이 회로도에 미연결 | 차별 | netlist, firmware | ✅ |
| R08 | 회로도에 연결됐는데 코드가 초기화 안 함 | 차별 | netlist, firmware | ✅ |
| R09 | 부팅 시 출력 나오는 핀에 부하 연결 | 기본 | netlist | ✅ |
| R10 | 회로도 변경 후 코드 미추종 (드리프트) | 차별 | netlist, firmware | ⬜ |
| R11 | 네트명이 주장하는 전압과 소스 부품의 전원 도메인이 다름 | 기본 | netlist | ✅ |
| R12 | 상위 전원 도메인이 하위를 직결 | 기본 | netlist | ✅ |

전체 11개. R6(I2C 풀업 누락)은 Flux Design Review가 이미 제공하므로 폐기했고, 번호를 재사용하지 않습니다.

---

## 규칙 추가하기

`.claude/skills/prefab-rule/SKILL.md` 참고. 요약하면:

1. 등급을 먼저 판정한다 (회로도만으로 되면 `기본`)
2. `NEEDS`에 필요한 입력을 선언한다
3. `check(ctx)`는 순수 함수 — 네트워크·LLM 호출 금지
4. 테스트 3개 필수: 양성 / 음성 / 미해결
5. 실제 보드 픽스처에 새 경고가 뜨면 발견인지 오탐인지 확인한다

```python
RULE_ID  = "R07"
TITLE    = "코드가 쓰는 핀이 회로도에 미연결"
SEVERITY = Severity.CRITICAL
TIER     = "차별"
NEEDS    = ["netlist", "firmware"]

def check(ctx) -> list[Finding]:
    ...
```

---

## 구조

```
src/prefab/
  types.py            Finding, Severity, Verdict, Evidence, Context
  text.py             한국어 조사 처리 (발견 문구가 그대로 노출된다)
  catalog.py          규칙 카탈로그 — 규칙 개수의 유일한 진실
  chips/              칩 제약 · 모듈 핀아웃 (docs/CHIPS.md 의 코드 사본)
  netlist/d356.py     IPC-D-356 파서
  netlist/graph.py    부품·네트 그래프, 전원 도메인, 수동 소자 판별
  netlist/pinmap.py   패드 → 실크 라벨 · GPIO 확정
  firmware/arduino.py 핀 사용 추출 (상수 추적 · 방향 · 못 읽은 자리 분류)
  bom.py              BOM CSV 파서
  datasheet/          데이터시트 사실 추출 · 사실 DB
  rules/              규칙 모듈 + 레지스트리
  engine.py           규칙 실행 → Finding 수집
  report.py           계약 응답 조립
web/service.py        검증 · 오류 · SQLite (FastAPI 를 모른다)
web/app.py            FastAPI 어댑터
tests/                규칙당 3개 + 실제 보드 골든 + 카탈로그 정합성 + 도구 중립성
```

---

## IPC-D-356 파싱 노트

이 형식으로 작업할 사람을 위해 알아낸 것을 남깁니다.

- 고정폭 레코드. 핀 이름 필드는 `[27:31]` — **4자에서 잘립니다**
  (`LP-GPIO0` → `LP-G`). 정확한 GPIO 번호는 모듈 핀아웃 DB 없이 알 수 없습니다.
- **MPN·부품값·제조사가 없습니다.** 데이터시트 기반 판정을 하려면 BOM이 반드시 필요합니다.
- **네트명은 `[3:17]` — 14자에서 잘립니다.** 핀 이름과 같은 문제인데 더 조용하게
  아픕니다. 이름 끝의 전압 표기가 날아가면 규칙이 아무 말도 안 하고, 서로 다른 두
  네트가 같은 14자로 뭉치면 **없는 연결이 생깁니다.** 우리 보드의 `_IN_ACTIVE_LOW` ·
  `D_POS_SWITCHED` 가 정확히 14자이고, 둘 다 **앞이** 잘린 흔적이 남아 있습니다.
- 릴레이 모듈처럼 여러 패드의 이름이 전부 같게 나오는 부품이 있습니다
  (6개 패드가 모두 `pad-`). **X좌표 클러스터링으로 제어부/스위치부를 분리**합니다.

---

## 관련 저장소

- [`prefab-web`](../prefab-web) — 프론트엔드

## 라이선스

MIT
