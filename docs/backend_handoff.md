# 백엔드 전달 사항 정리 (2026-07-07 기준)

> 프론트(강현) → 백엔드(조우진) 핸드오프 문서.
> 상세 계약은 `docs/backend_contract.md`, 스키마는 `docs/supabase_schema.sql` 참고.

## 1. 전달 문서 (이미 레포에 있음)

| 문서 | 내용 |
| :-- | :-- |
| `docs/backend_contract.md` | 앱이 읽는 테이블/컬럼, 쓰는 API 규격, 인증, 상태값 규약 전체 |
| `docs/supabase_schema.sql` | 확정 DB 스키마 |

## 2. 즉시 요청 (앱이 지금 막혀 있는 것) 🔴

1. **Realtime 활성화** — Supabase 대시보드에서 `tickets`, `waitings` 두 테이블 Realtime ON
   (Database → Replication). 꺼져 있으면 앱이 `RealtimeSubscribeException`으로 실패.
2. **Next.js API 5개 배포 + `API_BASE_URL` 공유** — 규격은 확정(계약 문서 3절), 배포만 남음:

   | 기능 | 엔드포인트 | 요청 → 응답 |
   | :-- | :-- | :-- |
   | 식권 구매 | POST `/api/tickets` | `{diningLineId}` → `{ticketId, qrToken, queueCount}` |
   | QR 검증(운영자) | POST `/api/tickets/verify` | `{qrToken}` → `{valid, status}` |
   | 대기 현황(보조) | GET `/api/lines/{id}/status` | → `{waitingCount, waitEstimateSec, level}` |
   | 원격 웨이팅 | POST `/api/waitings` | `{restaurantId}` → `{waitingId, queueNo}` |
   | AI 메뉴 검색 | POST `/api/ai/search` | `{query}` → `{answer, menus}` |

   인증: `Authorization: Bearer <Supabase accessToken>` (앱이 자동 첨부).
3. **QR 토큰 일치 확인** — 앱은 서버가 준 `qrToken`을 그대로 QR로 표시.
   운영자 대시보드 스캔 검증도 반드시 같은 `tickets.qr_token` 기준이어야 함.

## 3. 결정 필요 (같이 정하자) 🟡

1. **`called`(호출됨) 상태** — 앱 UI에는 "호출됨!" 표시가 있는데 DB `tickets.status`에는
   `'paid'|'used'|'expired'`뿐. 운영자가 호출하는 플로우를 살리려면
   `tickets.status`에 `'called'` 추가(또는 별도 컬럼) 필요. 시연 시나리오에 넣을지 결정.
2. **AI 응답 확장** — `/api/ai/search` 응답에 `lineId`/`restaurantId`(추천 대상 ID)를
   추가해주면 앱이 "추천 카드 탭 → 해당 라인/식당으로 이동"을 만들 수 있음. 선택사항.
3. **카카오 로그인** — 딥링크 `io.pnubapmukja://login-callback`을 Supabase 대시보드
   redirect URL에 등록 필요. 시연에 카카오 로그인 넣을지부터 결정.

## 4. 여유 있으면 (스키마 보강, 우선순위 낮음) 🟢

앱이 근사치로 때우고 있는 필드들 — 컬럼 추가 시 더 정확해짐:

- `restaurants`: 세부 카테고리(한식/일식…), 도보 시간, 할인 문구, 이모지/이미지
- `dining_lines`: 운영중/마감 상태
- 규모 커지면: 대기 인원 count 집계 RPC (지금은 앱이 tickets 전체 재조회)

## 5. 프론트 진행 상황 공유

- UI를 수정계획서 목업 기준으로 개선 중 (홈 완료, 이후 QR·제휴식당·AI 순).
  **화면 작업은 백엔드와 무관** — 계약만 안 바뀌면 영향 없음.
- 백엔드가 이 레포에서 직접 볼 파일은 `lib/data/supabase/`, `lib/data/api/` 3개뿐.
  통합 테스트는 레포 clone 후 `flutter run` (Realtime 켜져 있으면 Supabase 모드로 바로 붙음).
