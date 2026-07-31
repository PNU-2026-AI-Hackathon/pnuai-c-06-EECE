# 백엔드 연결 계약 (프론트 관점)

> 앱이 **실제로 읽고 쓰는 테이블·컬럼·API**를 정리한 문서.
> 백엔드(조우진) 실제 스키마와 이 문서가 다르면, 아래 "수정 위치"만 고치면 된다.

## 0. 접속 정보

- Project URL: `https://nnvqiigzlvgukvmrrama.supabase.co`
- anon key: `lib/core/env.dart`에 기본값으로 이미 박혀 있음 (공개용 키, RLS로 접근 제어).
- `lib/core/env.dart`의 `Env.useSupabase`가 true면 Supabase 연결, 아니면 Mock.
  → URL·anon key 둘 다 채워져야 true. 기본값을 넣어놨으니 **지금은 dart-define 없이 `flutter run`만 해도 Supabase 모드로 뜬다.**
- 강제로 Mock 시연 모드를 쓰고 싶으면 `flutter run --dart-define=SUPABASE_URL= --dart-define=SUPABASE_ANON_KEY=` 처럼 빈 값으로 덮어쓰면 됨.

**⚠️ 백엔드에 요청 필요 — Realtime 활성화:** `tickets`, `waitings` 두 테이블은 Supabase 대시보드에서 Realtime이 켜져 있어야 함
(Database → Replication, 또는 Table Editor → 테이블 클릭 → 상단 "Realtime" 토글). 꺼져 있으면 앱이
`RealtimeSubscribeException(status: channelError ...)`로 실패함. 프론트가 이 두 테이블 변화를 구독해서
실시간 대기 인원(학식)·웨이팅(제휴식당)을 계산하는 구조라 필요함 (2절 참고).

```bash
# 커스텀 API 배포되면:
flutter run --dart-define=API_BASE_URL=https://xxxx.vercel.app
```

## 1. DB 스키마 (확정 — 백엔드 4절 제공)

| 테이블 | 컬럼 | 앱에서 조회 |
| :-- | :-- | :-- |
| `users` | id(=auth.users.id), email, nickname, provider, college, role, created_at | 회원가입 시 트리거로 자동 생성됨. 앱은 직접 조회 안 함(Supabase Auth 세션만 사용). |
| `restaurants` | id, type('campus'\|'partner'), name, college_benefit, price_range, operating_hours(jsonb), is_waiting_available, created_at | ✅ |
| `dining_lines` | id, restaurant_id(FK), name, avg_service_sec(int, 초) | ✅ |
| `menus` | id, restaurant_id(FK), name, price, description, menu_date(date) | ✅ (식당 단위 — 라인별 컬럼 없음) |
| `tickets` | id, user_id(FK), dining_line_id(FK), status('paid'\|'used'\|'expired'), qr_token(unique), paid_at, used_at, expires_at | ✅ |
| `waitings` | id, user_id(FK), restaurant_id(FK), queue_no, status('waiting'\|'called'\|'done'\|'canceled'), created_at | ✅ |
| `coupons` | id, college, title, discount, valid_until | ✅ |
| `coupon_issues` | id, user_id(FK), coupon_id(FK), used, issued_at | 미사용 (쿠폰 발급/사용 이력 UI 생기면 사용) |
| `congestion_logs` | id, dining_line_id(FK), ts, waiting_count, wait_estimate | 미사용 (AI 학습용 로그, 앱은 tickets를 직접 세서 실시간 대기 인원 계산) |

## 2. 앱 모델 ↔ 실제 컬럼 매핑 (근사치 있음)

`dining_lines`·`restaurants`에는 "실시간 대기 인원" 컬럼이 없다. 대신:

- **라인 대기 인원** = `tickets`에서 `status='paid'`인 행을 `dining_line_id`별로 카운트.
- **식당 대기 팀 수** = `waitings`에서 `status='waiting'`인 행을 `restaurant_id`별로 카운트.
- 두 값 모두 `tickets`/`waitings` 테이블의 Realtime 변경을 "심박"으로 삼아, 변경이 감지될 때마다 관련 테이블을 다시 조회해서 재계산한다 (`lib/data/supabase/supabase_repositories.dart`).
  ⚠️ 데이터 규모가 커지면 매번 전체 재조회하는 지금 방식은 비효율적 — 그땐 백엔드 RPC(count 집계)나 `/api/lines/{id}/status`로 옮길 것.

`Restaurant`/`CafeteriaLine` 앱 모델에는 있는데 스키마엔 없는 필드는 근사치로 채움(`lib/data/supabase/supabase_mappers.dart`에 표시):

| 앱 필드 | 값 출처 | 비고 |
| :-- | :-- | :-- |
| `Restaurant.category` | `type` → '학식'/'제휴' | 실제 한식/일식 등 세부 카테고리 컬럼 없음 |
| `Restaurant.emoji` | `type` 기반 고정 이모지 | 컬럼 없음 |
| `Restaurant.walkMinutes` | 항상 0 | 컬럼 없음, 도보 거리 계산 근거 없음 |
| `Restaurant.discountText` | `college_benefit` → "○○ 대상 혜택" | 원래 의미(학생 할인 문구)와 다름, 근사 |
| `CafeteriaLine.location` | 소속 `restaurants.name` | 컬럼 없음 |
| `CafeteriaLine.status`(운영중/마감) | 항상 open | 컬럼 없음 |
| `MealTicket.queueNumber`/`aheadCount` | 같은 라인의 `status='paid'` 티켓을 `paid_at` 순으로 정렬한 순번 | 신규 구매 직후엔 `/api/tickets` 응답값이 더 정확(대기 목록 재조회 시에만 이 계산 사용) |
| `TicketStatus.called` | 발생 안 함 | DB에 대응 상태 없음(운영자가 부르는 상태가 tickets.status엔 없음) |
| `MealTicket`(status='expired') | `TicketStatus.used`로 합쳐서 표시 | 앱에 별도 만료 상태 없음 |

## 3. 앱이 쓰는 것 (커스텀 Next.js API — 🚧 규격 확정, 배포 진행 중)

`lib/data/api/api_client.dart`가 아래 계약대로 구현됨. `API_BASE_URL` 미설정 시 명확한 안내 예외를 던진다(앱은 SnackBar로 표시하고 죽지 않음).

| 기능 | 메서드·경로 | 요청 | 응답 |
| :-- | :-- | :-- | :-- |
| 식권 구매(대기열 등록) | POST /api/tickets | `{diningLineId}` | `{ticketId, qrToken, queueCount}` |
| QR 검증(운영자) | POST /api/tickets/verify | `{qrToken}` | `{valid, status}` |
| 대기 현황 조회 | GET /api/lines/{id}/status | - | `{waitingCount, waitEstimateSec, level}` |
| 원격 웨이팅 등록 | POST /api/waitings | `{restaurantId}` | `{waitingId, queueNo}` |
| 메뉴 자연어 검색 | POST /api/ai/search | `{query}` | `{answer, menus}` |

인증: Supabase 세션 accessToken을 `Authorization: Bearer`로 자동 첨부.

대기 현황은 Realtime(위 2절 방식)으로도 받을 수 있어, 실시간 화면은 그쪽을 우선 쓰고 `/api/lines/{id}/status`는 보조 수단(`ApiClient.lineStatus`)으로만 구현해둠.

**수정한 버그:** 식권 QR은 서버가 내려주는 `qrToken`(=DB `tickets.qr_token`)을 그대로 화면에 표시해야 운영자 검증과 일치한다. 기존 코드는 이 값을 버리고 로컬 문자열을 QR로 보여주고 있었음 — `MealTicket.qrToken` 필드를 추가하고 `qrData`가 이를 우선 사용하도록 수정함(Mock 모드는 기존처럼 로컬 문자열 유지).

## 4. 인증

- 이메일 로그인/회원가입: `lib/features/auth/`. 회원가입 성공 시 `users` 행이 트리거로 자동 생성됨.
- Supabase 모드에서 미로그인 시 자동으로 `/login`으로 보냄 (RLS 때문에 세션 필요).
- Mock 모드에서는 로그인 화면을 건너뛰고 바로 앱 진입.
- 카카오 로그인(`OAuthProvider.kakao`)은 딥링크(`io.pnubapmukja://login-callback`) + Supabase 대시보드 redirect URL 등록이 필요 → 아직 미구현, 백엔드와 값 맞춰서 추가 예정.

## 5. 로컬 개발 시 주의사항 (API_BASE_URL)

- Supabase는 클라우드라 실기기/에뮬레이터 어디서든 바로 붙음.
- 커스텀 API(Next.js)가 로컬(localhost)일 때: Android 에뮬레이터는 `http://10.0.2.2:3000`, 실제 폰은 PC의 LAN IP(`http://192.168.x.x:3000`)를 `API_BASE_URL`로 넣어야 함. (iOS 시뮬레이터는 `localhost` 그대로 가능)
- 가장 편한 방법: 백엔드를 Vercel에 배포하고 `https://...vercel.app`을 그대로 사용.
- Flutter는 네이티브 앱이라 브라우저 CORS 이슈는 없음 (웹 빌드 시엔 발생 가능).
- `service_role`(secret) 키는 프론트에 절대 넣지 않기 — `anon` key만 사용.
