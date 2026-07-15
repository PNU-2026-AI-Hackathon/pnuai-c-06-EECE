# 백엔드 전달 사항 정리

## 🔴 최신 요청 (2026-07-14) — 중간발표(7/23) 전 필수

프론트 완료: 운영자 대시보드 실서버 전환(tickets Realtime 대기열 집계) + **카메라 QR 스캔
(mobile_scanner) 동작 확인**. 이제 "학생 구매 → 운영자 스캔 → 학생 앱 사용완료" 체인이
실서버로 돌아감. 발표 전 백엔드에 필요한 것, 우선순위순:

### 1. verify 성공 시 다음 티켓 `called` 전이 (자동 호출의 마지막 조각) ⭐

- `POST /api/tickets/verify` 성공(티켓 used 처리) 직후, **같은 라인의 paid 티켓 중
  paid_at이 가장 빠른 1장을 `status='called'`로 업데이트**해주면 끝.
- `tickets.status` 허용값에 `'called'` 추가 필요 (paid/used/expired에).
- 프론트는 이미 완성: called 전환을 Realtime으로 감지 → 학생 폰에 푸시 알림.
  이거 하나면 시연의 하이라이트("스캔하자마자 다음 학생 폰이 울림")가 완성됨.
- 학생이 배식대 도착해 called 티켓을 스캔하면 그대로 used 처리 (별도 로직 불필요).

### 2. Vercel API CORS 헤더 (웹 배포 링크용)

- Netlify 웹 배포에서 구매/verify가 동작하려면 필요 (모바일 앱은 무관).
- 응답 헤더: `Access-Control-Allow-Origin: https://pnu-bapmukja.netlify.app`
  + `Access-Control-Allow-Headers: authorization, content-type`
  + OPTIONS 프리플라이트 200 응답.

### 3. Supabase Redirect 등록 (URL 확정 시)

- Auth → URL Configuration → Redirect URLs에
  `https://pnu-bapmukja.netlify.app`와 `https://pnu-bapmukja.netlify.app/**` 두 줄.
- Site URL도 같은 주소로 변경 (localhost면 로그인 후 남의 PC에서 localhost로 튕김).

### 4. 주변 상권 프록시 `GET /api/nearby` (웹용, 30분 작업)

프론트가 AI 추천에 카카오 로컬 API(부산대 주변 음식점)를 연결함. 모바일은 직접 호출로
동작하지만 **웹은 카카오가 CORS를 막아서 서버 프록시가 필요**. 카카오 응답 JSON을
그대로 중계하면 됨 (프론트는 이미 `/api/nearby`를 바라보게 구현돼 있음):

```ts
// app/api/nearby/route.ts
import { NextResponse } from 'next/server';

const KAKAO_URL =
  'https://dapi.kakao.com/v2/local/search/category.json' +
  '?category_group_code=FD6&x=129.0843&y=35.2318&radius=800&size=15&sort=distance';

export async function GET() {
  const res = await fetch(KAKAO_URL, {
    headers: { Authorization: `KakaoAK ${process.env.KAKAO_REST_KEY}` },
    next: { revalidate: 600 }, // 10분 캐시
  });
  return NextResponse.json(await res.json(), {
    headers: { 'Access-Control-Allow-Origin': '*' }, // 공개 데이터라 * 허용 무방
  });
}
```

- Vercel 환경변수 `KAKAO_REST_KEY` = 카카오 로그인에 쓰는 REST API 키
- 덤: 이 방식이 정착되면 모바일도 프록시로 전환해 키를 서버로 숨길 예정

**🆕 배포 확인 완료 (2026-07-15) — 확장 요청 2가지** (프론트는 이미 이 파라미터로 호출 중):

1. `?page=N` 지원 — 카카오는 페이지당 15곳뿐이라 가까운 순 15곳이 전부
   정문 앞 60m로 채워짐. page를 카카오에 그대로 전달해주면 45곳 확보 가능.
2. `?q=키워드` 지원 — 있으면 category 검색 대신 keyword 검색으로:
   `https://dapi.kakao.com/v2/local/search/keyword.json?query={q}&category_group_code=FD6&x=129.0843&y=35.2318&radius=1200&size=15&sort=distance`
3. radius를 800 → **1200**으로 (캠퍼스~부산대역 상권 커버)

```ts
// app/api/nearby/route.ts (수정판)
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const q = searchParams.get('q');
  const page = searchParams.get('page') ?? '1';
  const base = q
    ? `https://dapi.kakao.com/v2/local/search/keyword.json?query=${encodeURIComponent(q)}`
    : 'https://dapi.kakao.com/v2/local/search/category.json?';
  const url = `${base}&category_group_code=FD6&x=129.0843&y=35.2318&radius=1200&size=15&page=${page}&sort=distance`;
  const res = await fetch(url, {
    headers: { Authorization: `KakaoAK ${process.env.KAKAO_REST_KEY}` },
    next: { revalidate: 600 },
  });
  return NextResponse.json(await res.json(), {
    headers: { 'Access-Control-Allow-Origin': '*' },
  });
}
```

### 5. 여유 시: 식단 수집 크론 (아래 2026-07-09 섹션 참고)

---

## 📌 현재 상태 요약 (2026-07-08 2차 갱신)

**완료된 것**: 카카오 OAuth 로그인 ✅ · Supabase 조회 ✅ · **AI 추천 ✅ (프론트가 Gemini
무료 API로 직접 연결 — `/api/ai/search`는 급하지 않음)** · 운영자 대시보드 Mock ✅
**앱 쪽 준비 상태**: API 계약대로 호출하는 코드 전부 구현 완료 — 배포되는 즉시 자동 연결됨.

### 지금 백엔드가 해야 할 것 (우선순위순)

1. **`tickets` 테이블 Realtime 활성화** (5분) — Supabase 대시보드 → Database → Replication.
   이거 없으면 Supabase 모드에서 실시간 대기/식권 화면이 에러남. **최우선.**
2. **Next.js API 2개 구현·배포 + `API_BASE_URL` 공유** (핵심 작업)
   - `POST /api/tickets` {diningLineId} → {ticketId, qrToken, queueCount} — 식권 구매
   - `POST /api/tickets/verify` {qrToken} → {valid, status} — 운영자 QR 검증
   - ~~`POST /api/ai/search`~~ Gemini로 임시 해결 — 여유 생기면 서버로 이전 (키 보호 목적).
     이전 시 프론트 `gemini_ai_repository.dart`의 프롬프트를 그대로 쓰면 됨.
   - ~~`POST /api/waitings`~~ 인근 상권 배제로 당장 불필요
3. **🆕 자동 호출 로직 설계 (같이 결정)** — 프론트에 "자리가 나면 자동으로 다음 번호
   호출 → 학생 알림" 컨셉이 확정됨 (운영자 대시보드 Mock으로 구현/시연 중).
   실서버 구현 방향 제안:
   - `verify` 성공(배식 완료) 시 서버가 같은 라인의 다음 대기 티켓 상태를 `called`로 전이
   - → `tickets.status`에 `'called'` 값 추가 필요 (기존 paid/used/expired에)
   - 앱은 Realtime으로 called 전환을 이미 감지·알림함 (프론트 추가 작업 없음)
4. **시드 데이터 입력** — 금정회관 restaurants/dining_lines/menus 행.
   식당 협의 전엔 임시값: 3개 라인, 4,000원, avg_service_sec 25초.
5. **웹 배포 URL Redirect 등록** — 프론트 배포 URL을 Supabase Redirect URLs에 추가.
6. **확인**: 카카오 가입 시 `users` 행 트리거 생성 여부 (성공 사례 1건).

### 🆕 dining_lines 중복 시드 정리 (2026-07-13 추가) 🔴

통합 테스트 성공! (구매 → QR → 대기번호까지 실서버 동작 확인)
다만 **같은 이름의 라인이 중복 시드**되어 홈에 "1층 정식" "1층 일품"이 2개씩 뜸.
프론트에 이름 기준 중복 제거를 넣어 화면은 정리했지만, **대기열이 두 행으로 쪼개지면
대기번호가 실제와 어긋나므로 DB에서 중복 행을 지워야 함**:

```sql
-- 이름별로 티켓이 가장 많이 달린 행(=실사용 행) 하나만 남기고 삭제
with ranked as (
  select d.id,
         row_number() over (
           partition by d.name
           order by (select count(*) from tickets t where t.dining_line_id = d.id) desc,
                    d.id
         ) as rn
  from dining_lines d
)
delete from dining_lines
where id in (select id from ranked where rn > 1);
```

(⚠️ 삭제될 행을 티켓이 참조 중이면 FK 에러가 남 — 그 경우 먼저
`update tickets set dining_line_id = <남길 행 id> where dining_line_id = <지울 행 id>;`)

또 하나 결정: 현재 "2층 정식"과 "2층 교직원 정식"이 둘 다 있음. 금정회관 2층은
교직원식당 하나(정식 6,500원)뿐이니 **한 행으로 통일 권장** — 이름은 "2층 교직원 정식".

### 🆕 식단 자동 수집 (서버 크론 요청 — 2026-07-09 추가)

프론트가 부산대 공식 식단 페이지 파싱을 구현·검증 완료함. **수집 URL 파라미터 확보**:

- 금정회관 학생식당(주간, 중식/석식):
  `https://www.pusan.ac.kr/kor/CMS/MenuMgr/menuListOnBuilding.do?mCode=MN202&campus_gb=PUSAN&building_gb=R001&restaurant_code=PG002`
- 금정회관 교직원식당(주간, 중식): 같은 URL에서 파라미터 없이 (기본값)
- 공식 운영시간: 학생식당 중식 11:00-17:00 / 석식 17:00-18:30 (조식 방학 미운영), 교직원 중식 11:00-15:00
- 확인된 가격: 학생 정식/일품 각 5,000원, 교직원 정식 6,500원 → **menus 시드에 이 값 사용**

**요청**: 앱은 웹(CORS)에서 이 페이지를 직접 못 읽음 → 서버에서 주 1회(월요일 아침) 크론으로
수집해 `menus` 테이블에 넣어주면 웹 포함 전 플랫폼에서 실식단이 뜸.
파싱 로직은 `lib/data/api/pnu_menu_service.dart` (_parseBuildingWeek/_parseSections)를
그대로 이식하면 됨 — 열=날짜, 행=중식/석식, 셀 내 "정식-5,000원<br>메뉴..." 구조.

### 백엔드 테스트 방법 (앱/에뮬레이터 불필요)
- API: curl/Postman으로 위 규격 검증 (Authorization: Bearer <Supabase accessToken>)
- 통합: 프론트 웹 배포 링크 열어서 브라우저로 직접 확인

---

# (이하 상세 계약 — 2026-07-07 작성)

> 프론트(강현) → 백엔드(조우진) 핸드오프 문서.
> 상세 계약은 `docs/backend_contract.md`, 스키마는 `docs/supabase_schema.sql` 참고.

## ⚠️ 범위 변경 (2026-07-07): 인근 상권(제휴식당) MVP에서 배제

앱에서 제휴식당 탭·원격 웨이팅·쿠폰 화면을 제거함 (코드는 보존, 라우트만 차단).
백엔드 영향:

- **불필요해진 것**: `POST /api/waitings`, `waitings` Realtime, `coupons`/`coupon_issues` — 당장 구현 안 해도 됨
- **여전히 필요한 것**: `tickets` Realtime, `POST /api/tickets`, `/api/tickets/verify`, `/api/ai/search`
- 스키마는 그대로 둬도 됨 (추후 복구 대비)

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
4. **카카오 OAuth 설정 (필수로 승격 — 회원가입/로그인이 카카오 전용으로 확정됨)**
   1) [Kakao Developers](https://developers.kakao.com)에 앱 등록, REST API 키 발급
   2) Kakao 콘솔 → 카카오 로그인 활성화, Redirect URI에
      `https://nnvqiigzlvgukvmrrama.supabase.co/auth/v1/callback` 등록
   3) Supabase 대시보드 → Auth → Providers → Kakao 활성화 (REST API 키/Secret 입력)
   4) Supabase → Auth → URL Configuration → Redirect URLs에
      `io.pnubapmukja://login-callback` 추가

   **프론트는 이미 완료**: 딥링크(AndroidManifest/Info.plist), `signInWithOAuth(kakao)`
   호출, 로그인 화면 카카오 버튼. 위 4단계만 끝나면 즉시 동작함.
   `users` 트리거가 OAuth 가입(email/nickname이 카카오에서 옴)도 처리하는지 확인 필요.

## 3. 결정 필요 (같이 정하자) 🟡

1. **`called`(호출됨) 상태** — 앱 UI에는 "호출됨!" 표시가 있는데 DB `tickets.status`에는
   `'paid'|'used'|'expired'`뿐. 운영자가 호출하는 플로우를 살리려면
   `tickets.status`에 `'called'` 추가(또는 별도 컬럼) 필요. 시연 시나리오에 넣을지 결정.
2. **AI 응답 확장** — `/api/ai/search` 응답에 `lineId`/`restaurantId`(추천 대상 ID)를
   추가해주면 앱이 "추천 카드 탭 → 해당 라인/식당으로 이동"을 만들 수 있음. 선택사항.
3. ~~카카오 로그인 포함 여부~~ → **확정됨: 카카오 전용** (위 🔴 4번 참고)

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
