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
| 구현된 규칙 | **2 / 12** (R11, R12 — 둘 다 "기본" 등급) |
| 펌웨어 정적 분석 | ⬜ 미구현 |
| 데이터시트 파이프라인 | ⬜ 미구현 |
| 부품 사실 DB | **0 부품** |
| GitHub Action | ⬜ 미구현 |

### 알려진 문제
- R11과 R12가 같은 네트에 중복 검출됨 (dedup 필요)

---

## 빠른 시작

```bash
git clone <repo> && cd prefab-api
uv sync                     # 또는 pip install -e ".[dev]"
pytest -q

# 실제 보드로 돌려보기
python -m prefab tests/fixtures/esp32c6presencesmartlight.d356

# API 서버
uvicorn web.app:app --reload
```

---

## API

전체 스펙은 [`API_CONTRACT.md`](./API_CONTRACT.md).

```
POST   /api/v1/checks          검사 생성 (multipart: netlist, bom?, firmware?)
GET    /api/v1/checks/{id}     결과 조회
GET    /api/v1/rules           규칙 카탈로그
GET    /healthz
```

```bash
curl -F "netlist=@board.d356" https://<host>/api/v1/checks
```

응답의 `pipeline` 배열은 **못 한 단계도 그대로 싣습니다.** BOM이 없으면
데이터시트 단계가 `skipped`로 오고 사유가 붙습니다. 규칙을 못 돌렸는데
"이상 없음"처럼 보이는 응답은 만들지 않습니다.

---

## 규칙 카탈로그

`기본` 등급은 기존 상용 도구가 이미 제공하는 범위, `차별`은 Prefab만 하는 것입니다.

| ID | 규칙 | 등급 | 필요 입력 | 상태 |
|---|---|---|---|---|
| R1 | 코드가 입력 전용 핀(GPIO34~39)에 OUTPUT 설정 | 차별 | netlist, firmware | ⬜ |
| R2 | 회로도가 SPI flash 핀(GPIO6~11)에 연결 | 기본 | netlist | ⬜ |
| R3 | strapping 핀 부팅 상태 오류 | 기본 | netlist | ⬜ |
| R4 | 외부 부품 출력이 GPIO 입력 최대 초과 | 기본 | netlist, datasheet | ⬜ |
| R5 | ADC2 사용 + 같은 빌드에 WiFi 초기화 | 차별 | firmware | ⬜ |
| R7 | 코드가 쓰는 핀이 회로도에 미연결 | 차별 | netlist, firmware | ⬜ |
| R8 | 회로도에 연결됐는데 코드가 초기화 안 함 | 차별 | netlist, firmware | ⬜ |
| R9 | 부팅 시 출력 나오는 핀에 부하 | 기본 | netlist | ⬜ |
| R10 | 회로도 변경 후 코드 미추종 (드리프트) | 차별 | netlist, firmware, git | ⬜ |
| R11 | 네트명이 주장하는 전압 ≠ 소스 부품 전원 도메인 | 기본 | netlist | ✅ |
| R12 | 상위 전원 도메인이 하위를 직결 | 기본 | netlist | ✅ |

R6(I2C 풀업 누락)은 Flux Design Review가 이미 제공하므로 폐기했습니다.

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
  types.py          Finding, Severity, Verdict, Evidence, Context
  netlist/d356.py   IPC-D-356 파서
  netlist/graph.py  부품·네트 그래프, X좌표 패드 클러스터링
  firmware/         펌웨어 정적 분석 (예정)
  datasheet/        데이터시트 사실 추출 (예정)
  rules/            규칙 모듈 + 레지스트리
  engine.py         규칙 실행 → Finding 수집
web/app.py          FastAPI
tests/              규칙당 3개 + 실제 보드 골든 테스트
```

---

## IPC-D-356 파싱 노트

이 형식으로 작업할 사람을 위해 알아낸 것을 남깁니다.

- 고정폭 레코드. 핀 이름 필드는 `[27:31]` — **4자에서 잘립니다**
  (`LP-GPIO0` → `LP-G`). 정확한 GPIO 번호는 모듈 핀아웃 DB 없이 알 수 없습니다.
- **MPN·부품값·제조사가 없습니다.** 데이터시트 기반 판정을 하려면 BOM이 반드시 필요합니다.
- 릴레이 모듈처럼 여러 패드의 이름이 전부 같게 나오는 부품이 있습니다
  (6개 패드가 모두 `pad-`). **X좌표 클러스터링으로 제어부/스위치부를 분리**합니다.

---

## 관련 저장소

- [`prefab-web`](../prefab-web) — 프론트엔드

## 라이선스

MIT
