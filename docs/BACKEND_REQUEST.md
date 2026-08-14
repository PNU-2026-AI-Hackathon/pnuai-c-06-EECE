# 백엔드 작업 요청 (FastAPI)

프론트엔드는 완성되어 있고, 현재 목 데이터로 동작합니다.
**`lib/data.ts` 한 파일만 fetch로 바꾸면 연동이 끝나도록** 설계했으니, 아래 계약대로 API를 만들어주세요.

계약은 세 파일로 나뉩니다.

| 파일 | 범위 |
|---|---|
| `types/index.ts` | 매장·업로드·주간분석·예측·검증·콘텐츠 |
| `types/recommendation.ts` | 행동 추천·실행 행동·데이터 신선도 |
| `types/agent.ts` | 에이전트 실행 기록·도구·정책·성적표 |

## 계약의 원천

**`types/index.ts` 가 유일한 계약입니다.** 응답 JSON의 필드명·타입을 이 파일과 정확히 맞춰주세요 (camelCase 그대로).
Pydantic 모델을 새로 설계하지 말고 이 타입을 옮겨 적는 방식을 권합니다.

참고 구현: `scripts/build-store-data.mjs` + `scripts/lib/csv-model.mjs` 에
파싱→집계→예측→백테스트 로직이 JS로 이미 작동합니다. 이걸 Python으로 포팅하면 됩니다.
실제 응답 예시는 `mocks/generated/store-data.json` (술집 CSV에서 생성된 진짜 계산 결과)를 보세요.

## 필요한 엔드포인트 (우선순위 순)

| # | 메서드/경로 | 응답 타입 (types/index.ts) | 비고 |
|---|---|---|---|
| 1 | `POST /stores/{storeId}/uploads` (multipart CSV) | `UploadResult` | 파싱·정규화·경고. 동기 처리로 시작해도 됨 |
| 2 | `GET /stores/{storeId}/analysis/weekly` | `WeeklyAnalysis` | 최근 완료된 주. `?week=YYYY-MM-DD` 옵션 |
| 3 | `GET /stores/{storeId}/forecast` | `Forecast` | 다음 주. **evidence contribution 합 == expectedChangeRate 필수** |
| 4 | `GET /stores/{storeId}/verification` | `ForecastVerification \| null` | 백테스트. 첫 주면 null |
| 5 | `GET /stores/{storeId}` | `Store` | |
| 6 | `GET /stores/{storeId}/early-sales-ends` | `EarlySalesEnd[]` | 시각 데이터 없으면 빈 배열 + 이유 |
| 6b | `PATCH /early-sales-ends/{id}` | `EarlySalesEnd` | 사장님 확인 `{ ownerConfirmation, ownerNote }` |
| 7 | `POST /stores/{storeId}/content` | `ContentGeneration` | 후순위. LLM 프롬프트에 forecast·missed 주입 |

## 에이전트 (Phase 2 — 여기가 제품의 핵심입니다)

STAFFI는 사장님이 열어봐야 도는 대시보드가 아니라 **스스로 돌고 먼저 알리는 AI 직원**입니다.
위 1~7번은 "도구"이고, 아래가 그 도구를 쓰는 "직원"입니다.

### 에이전트 루프

```
트리거 (cron "0 8 * * 1" / 새 데이터 도착 / 학사일정 D-3)
   ↓
도구 호출 — LLM이 숫자를 만들지 않고 도구에서 "가져온다"
   ↓
판단 — 알릴 만한가? (AgentPolicy.changeRateThreshold 등)
   ↓
추천 생성 → 알림 발송 → 사장님 승인 → 행동 실행
   ↓
AgentRun으로 전 과정 기록 (감사 로그 겸 화면 타임라인)
```

### 도구 화이트리스트 (`AgentToolName`)

목록에 없는 일은 하지 않습니다. 전부 위 1~7번 엔드포인트나 내부 함수로 이미 존재합니다.

| 도구 | 대응 |
|---|---|
| `analyze_weekly` | 2번 |
| `forecast_next_week` | 3번 |
| `verify_last_forecast` | 4번 |
| `detect_early_sales_end` | 6번 |
| `get_academic_events` | 학사일정 DB |
| `check_data_freshness` | 신규 (아래 참고) |
| `generate_content` | 7번 |
| `send_notification` | 알림톡 발송 |

### 추가 엔드포인트

| # | 메서드/경로 | 응답 타입 | 비고 |
|---|---|---|---|
| 8 | `POST /stores/{id}/agent/runs` | `AgentRun` | 에이전트 1회 실행 (스케줄러·수동 공용) |
| 9 | `GET /stores/{id}/agent/runs` | `AgentRun[]` | 활동 타임라인. 최신순, `?limit=` |
| 10 | `GET /stores/{id}/recommendations` | `Recommendation[]` | `?status=proposed` 기본 |
| 11 | `PATCH /recommendations/{id}` | `Recommendation` | `{ status, declineReason }` — **학습 신호** |
| 12 | `POST /actions/{id}/approve` | `AgentAction` | 승인 후에만 실행. 승인 없이 `executed` 금지 |
| 13 | `GET /stores/{id}/agent/health` | `AgentHealth` | 예측 평균 오차·추천 채택률 |
| 14 | `GET /stores/{id}/data-freshness` | `DataFreshness` | 마지막 데이터 경과일 |
| 15 | `GET/PUT /stores/{id}/agent/policy` | `AgentPolicy` | 자율성 등급·알림 시각 |

### 에이전트 규칙 (제품 규칙만큼 중요)

1. **LLM에게 계산을 시키지 마세요.** 통계는 pandas가, LLM은 도구 결과를 받아 해석·문장 생성만. `AgentStep.summary`의 숫자는 반드시 도구 반환값에서 나와야 합니다
2. **자율성은 L2가 상한** — `AgentPolicy.autonomyLevel` 기본값 `recommend_with_approval`. 비용 발생·외부 노출 행동(`schedule_post`, `draft_order`)은 `requiresApproval: true` 강제, 승인 없이 실행하면 안 됩니다
3. **모든 단계를 기록** — 건너뛴 단계도 `status: "skipped"` + `reason`으로 남깁니다. 화면에 "왜 안 했는지"가 그대로 표시됩니다
4. **알릴 게 없으면 알리지 않습니다** — 임계치 미만이면 `notified: false` + `skipReason`. 매주 의미 없는 알림은 이탈을 만듭니다
5. **추천에는 근거가 최소 1개** — `Recommendation.evidence[].source`에 "매장 데이터 33주"처럼 출처를 적습니다
6. **`quietHours` 준수** — 새벽 영업 중인 사장님께 8시 알림이 가면 안 됩니다

응답 예시는 `mocks/agent.ts` · `mocks/recommendation.ts` 를 골든 샘플로 쓰세요.
2025-10-20 중간고사 주 실행을 실제 수치로 재현해 뒀습니다.

### 데이터 신선도 (`check_data_freshness`)

구독 유지의 핵심 장치입니다. 1년치를 한 번 넣고 끝나면 예측이 낡아갑니다.

| 경과 | level | 동작 |
|---|---|---|
| ~14일 | `fresh` | 정상 예측 |
| 15~28일 | `aging` | 예측 + "데이터가 N주 지났습니다" 경고 |
| 29일~ | `stale` | **예측 중단** (`blocksForecast: true`) + 새 파일 요청 |

### DB 테이블 추가 (기획서 §62에 이어서)

```sql
agent_runs         (id, store_id, trigger_kind, status, started_at, finished_at,
                    headline, notified, skip_reason, error)
agent_steps        (id, run_id, order, tool, label, status, started_at,
                    duration_ms, summary, reason)
early_sales_ends   (id, store_id, date, menu_name, last_sold_at, usual_closing_at,
                    earlier_by_minutes, opportunity_low, opportunity_high, repeated_weeks,
                    possible_causes JSONB, reasoning, confidence,
                    owner_confirmation, owner_note)
recommendations    (id, store_id, run_id, type, priority, action, description,
                    evidence JSONB, confidence, action_window_start, action_window_end,
                    estimated_impact, status, decided_at, decline_reason, created_at)
agent_actions      (id, recommendation_id, kind, title, preview, requires_approval,
                    reversible, execute_by, status, executed_at, result_summary)
agent_notifications(id, run_id, channel, title, body, sent_at, read_at, deep_link)
agent_policies     (store_id, autonomy_level, schedule, channels, quiet_hours,
                    change_rate_threshold, repeat_weeks_threshold)
```

### 스케줄러

APScheduler 또는 Celery beat. 매장별 `AgentPolicy.schedule`(cron)을 읽어 실행하고,
결과를 `agent_runs`에 남긴 뒤 알림톡을 발송합니다. 실패해도 실행 기록은 반드시 남겨주세요
(`status: "failed"` + 사장님이 읽어도 되는 `error` 문장).

## 반드시 지켜야 하는 제품 규칙 (README 설계 원칙과 동일)

1. **예측에는 근거가 붙는다** — `Forecast.evidence[].contribution`의 합이 `expectedChangeRate`와 정확히 일치해야 합니다. 프론트가 합계를 검증해서 불일치하면 빨간 경고를 띄웁니다. 곱셈 모형이면 로그 분해를 쓰세요 (`decomposeContributions` 참고).
2. **추측하지 않는다** — 데이터가 부족하면 `expectedChangeRate: null` + `dataSufficiency.level: "insufficient"` + 사장님이 읽을 `message`. 현재 기준: 8주 미만이면 예측 금지.
3. **만들 수 없는 값은 비운다** — 결제 시각 없는 CSV면 `hourlySales: []`, 조기 종료 후보는 빈 배열. 임의로 채우지 마세요.
4. **`origin` 필드는 3단계입니다** — 프론트가 이 값으로 배지를 자동 표시합니다. 셋을 섞으면 화면이 전부 목업으로 보입니다.

   | 값 | 언제 | 화면 |
   |---|---|---|
   | `real` | 실제 매장 POS 파일을 파이프라인이 계산한 값 | 배지 없음 |
   | `computed` | **예시 CSV**를 실제 파이프라인이 그대로 계산한 값 | "예시 데이터로 계산" |
   | `sample` | 사람이 손으로 적어 넣은 값 (아직 엔진이 없는 기능) | "예시 데이터" |

   판정 기준은 **입력 데이터의 출처**입니다. 계산 경로가 같아도 입력이 예시 파일이면 `computed`이고,
   계산을 아예 안 하고 문구를 지어냈으면 `sample`입니다. 예: 홍보 콘텐츠는 생성 엔진이 붙기 전까지 `sample`.
5. 사장님에게 보이는 `message`·`errorAnalysis`·`reasoning` 문장은 **존댓말 한국어**로, 전문용어 없이.
6. **품절을 확정하지 않는다** — 판매가 일찍 끝난 것은 `EarlySalesEnd` 후보로만 내리고, `possibleCauses`에 원인 후보를 담습니다. `ownerConfirmation`은 사장님이 6b로 확정하기 전까지 `"unconfirmed"`입니다. 금액도 단일 값이 아니라 `opportunityRange`로 내려주세요.
7. **오차 원인을 확정하지 않는다** — `errorAnalysis`는 "비 때문입니다"가 아니라 "가능한 원인으로 …가 있지만 확인이 필요합니다" 형태로 씁니다.
8. **예측은 범위로** — `expectedRange`(하한·상한·coverage)와 `comparableCases`(같은 이벤트 사례 수)를 반드시 채웁니다. 신뢰 수준은 데이터 기간이 아니라 **사례 수**로 정합니다 (3회↑ high / 2회 medium / 1회 low).

### 프론트가 검증하는 것 (백엔드를 믿지 않습니다)

화면이 응답을 그대로 믿지 않고 다음을 확인합니다. 어긋나면 숫자 대신 경고를 띄웁니다.

- `Forecast.evidence[].contribution`의 합 == `expectedChangeRate` (허용 오차 0.05%p)
- `DataFreshness.blocksForecast`가 true면 예측을 아예 렌더링하지 않음
- `hourlySales`가 빈 배열이면 차트 자리에 "만들 수 없는 이유"를 표시

`?scenario=mismatch` 로 합계 불일치 화면을 직접 확인할 수 있습니다.

## CSV 입력 스펙 (두 가지 형태 모두 처리)

**A. 일별 집계형** (현재 샘플: `data/pub-sales-pnu-2025.csv`)
`date, 요일, 학사이벤트, {메뉴}_판매수량..., 총판매수량, 총매출, 주_시작일` — BOM 있음, UTF-8.
단가 컬럼이 없으므로 최소제곱 역산 (참고 구현 `estimateMenuPrices`, 샘플에서 오차 0%).

**B. 결제 내역형** (카페 목 데이터가 가정하는 형태)
행 단위 결제(시각 포함) → 시간대별 매출·품절 추정 가능. 메뉴명 오염("아아", "ICE아메리카노") 정규화 필요 → `MenuNormalization[]`로 반환, confidence < 0.8이면 프론트가 확인 UI 표시.

## 예측 모델 (참고 구현 그대로)

```
일매출 = 기준(일반학기 평균) × 요일계수 × 학사이벤트계수 × 최근3주추세
```

- 백테스트 결과(술집 CSV, 학습 33주): 중간고사 주 예측 범위 −32~−22% vs 실제 −24% (범위 안), 중앙값 −27%
- 범위는 과거 주간 예측 오차의 20~80% 분위에서 만들고, 같은 이벤트 표본이 10일 미만이면 `√(10/표본일수)` 만큼 넓힙니다 (`forecastSpread` 참고)
- 검증 엔드포인트는 대상 주 **이전 데이터만으로** 재학습해 예측→실제 비교 (미래 누출 금지)
- 학사일정: 샘플 CSV엔 라벨이 있지만, 실서비스는 부산대 학사일정을 서버가 보유해야 합니다 (`mocks/academic-calendar.ts` 참고)

## 기타

- CORS: `http://localhost:3000` 허용
- 에러는 `{ "detail": "사장님이 읽어도 되는 한국어 문장" }` 형태
- 날짜는 전부 `YYYY-MM-DD` 문자열 (타임존 계산 금지, `types/index.ts`의 ISODate 참고)
- OpenAPI 스키마가 나오면 프론트에서 타입 대조하겠습니다

## 프론트 연동 지점 (참고)

```ts
// lib/data.ts — 현재
export async function getForecast(): Promise<Forecast> { return generatedForecast; }
// 연동 후
export async function getForecast(storeId: string): Promise<Forecast> {
  const res = await fetch(`${API_BASE}/stores/${storeId}/forecast`, { next: { revalidate: 3600 } });
  return res.json();
}
```

질문은 프론트 담당(강현)에게. `mocks/generated/store-data.json`을 응답 골든 샘플로 쓰면 됩니다.
