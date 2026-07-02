# PNU 밥묵자 🍚

> 부산대 학생식당 · 지역상권 통합 웨이팅 플랫폼
> 제7회 PNU 창의융합AI해커톤 창업트랙(PAI+X) — 팀 전전컴

부산대 학생이 점심시간에 빠르게 식사 장소를 결정하도록 돕는 모바일 앱.
학식 라인별 실시간 대기 현황, 모바일 QR 식권, 대기번호 발급, 인근 제휴 식당 원격 웨이팅·할인 쿠폰, AI 메뉴 추천을 제공한다.

📄 상세 기획: [PNU밥묵자_수정사업계획서](./PNU밥묵자_수정사업계획서%20(1).md)

---

## 핵심 기능 (MVP)

| # | 기능 | 상태 |
| :-- | :-- | :-- |
| 1 | 학식 라인별(1층 정식·1층 단품·2층 정식) 실시간 대기 현황 | 🔲 |
| 2 | 모바일 QR 식권 구매 + 대기번호 동시 발급 | 🔲 |
| 3 | 호출 상태 화면 (대기 → 호출 → 완료) | 🔲 |
| 4 | 인근 제휴 식당 원격 웨이팅 | 🔲 |
| 5 | 학생 할인 쿠폰 | 🔲 |
| 6 | AI 메뉴 검색·혼잡도 기반 추천 | 🔲 |
| 7 | 운영자 QR 스캔 체크인 (데모) | 🔲 |

핵심 도메인 로직: **식권 구매 = 대기열 자동 등록** → 배식대 QR 스캔 시 대기열에서 제거 (계획서 2.3)

## 기술 스택

```txt
Framework        : Flutter 3.x (stable) / Dart 3
State Management : flutter_riverpod 2.x (codegen 미사용)
Routing          : go_router (하단 탭바 = StatefulShellRoute)
QR 표시          : qr_flutter
QR 스캔          : mobile_scanner (운영자 체크인 데모)
Local Storage    : shared_preferences
Backend          : Supabase (추후 연동 — supabase_flutter)
Realtime         : Supabase Realtime (추후) / MVP는 Mock Stream 시뮬레이터
Mock Data        : Repository 패턴으로 추상화, MVP 기간 우선 사용
```

### 데이터 계층 원칙

서버 완성 여부와 무관하게 앱이 동작해야 한다.

```
UI (Riverpod Provider)
   ↓
abstract Repository (인터페이스)
   ↓                    ↓
MockRepository      SupabaseRepository
(지금 — Stream+Timer   (추후 — Realtime 교체,
 실시간 시뮬레이션)      UI 코드 변경 없음)
```

## 프로젝트 구조 (예정)

```
lib/
├── main.dart
├── app/                  # MaterialApp, 라우터, 테마
├── core/                 # 공통 상수·유틸·확장
├── data/
│   ├── models/           # CafeteriaLine, Ticket, Restaurant, Coupon ...
│   ├── repositories/     # abstract + mock 구현
│   └── mock/             # Mock 데이터 소스, 대기열 시뮬레이터
└── features/
    ├── home/             # 학식 라인별 대기 현황
    ├── ticket/           # QR 식권 구매·발급·호출 상태
    ├── restaurants/      # 제휴 식당 웨이팅·쿠폰
    ├── ai/               # AI 메뉴 검색·추천 (Mock)
    └── profile/          # 내 정보·식권 이력
```

## 실행 방법

```bash
flutter pub get
flutter run          # Android Emulator (Pixel API 34 권장)
```

## 개발 원칙

- 모바일 앱 중심 MVP. 웹(Next.js/PWA) 구조 아님
- Android Emulator에서 즉시 실행 가능해야 함
- iOS·Android 단일 코드베이스
- 실제 결제·OAuth·AI API는 붙이지 않음 — 먼저 Mock으로 시연 완성도 확보
- 엔터프라이즈 구조보다 MVP 완성도 우선, 단 Supabase 확장 가능하게 Repository로 추상화
- 최우선 UX: QR 식권, 대기번호, 호출 상태, 하단 탭바

## 일정

| 단계 | 기간 | 작업 |
| :-- | :-- | :-- |
| 핵심 개발 | ~7월 | 스캐폴딩 → Mock 데이터 계층 → 핵심 화면(대기현황·식권·호출) |
| AI·연동 | 7월 말 | AI 추천(Mock→실연동 검토), Supabase 연동 |
| 테스트·배포 | 8월 | 통합 테스트, 학내 베타 (APK 직배포) |
| 본선 | **8/28** | 시연·발표 |

## 팀

| 이름 | 역할 |
| :-- | :-- |
| 권지효 | PM·총괄, AI 데이터 테스트 |
| 한지양 | 기획, AI 데이터 분석 |
| 유동훈 | DB |
| 조우진 | 백엔드 |
| 박강현 | **프론트엔드(Flutter)**·DB, 디버깅 |
