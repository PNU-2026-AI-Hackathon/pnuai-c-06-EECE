import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../core/env.dart';
import '../data/mock/mock_campus_data_source.dart';
import '../data/mock/mock_repositories.dart';
import '../data/models/cafeteria_line.dart';
import '../data/models/coupon.dart';
import '../data/models/meal_ticket.dart';
import '../data/models/remote_waiting.dart';
import '../data/models/restaurant.dart';
import '../data/api/api_client.dart';
import '../data/api/api_ai_repository.dart';
import '../data/api/gemini_ai_repository.dart';
import '../data/api/pnu_menu_service.dart';
import '../data/mock/mock_ai_repository.dart';
import '../data/repositories/ai_repository.dart';
import '../data/repositories/cafeteria_repository.dart';
import '../data/repositories/restaurant_repository.dart';
import '../data/repositories/ticket_repository.dart';
import '../data/supabase/supabase_repositories.dart';

/// ── 데이터소스 전환 스위치 ──────────────────────────────
/// 시연(Mock) 모드 — 런타임 전환 가능.
/// true면 Supabase 연결 여부와 무관하게 Mock 데이터로 동작한다.
/// (시연 중 서버/네트워크 장애 시 즉시 폴백하는 용도)
final demoModeProvider = StateProvider<bool>((ref) => false);

/// 실제 Supabase 사용 여부 = 빌드 설정(Env) AND 시연 모드 꺼짐.
/// 아래 모든 repository가 이 값을 watch하므로, 스위치를 켜면
/// 화면 수정 없이 전체 데이터가 Mock으로 즉시 전환된다.
final useSupabaseProvider = Provider<bool>(
  (ref) => Env.useSupabase && !ref.watch(demoModeProvider),
);

/// Mock 데이터소스 (Supabase 모드에선 생성되지 않음)
final campusDataSourceProvider = Provider<MockCampusDataSource>((ref) {
  final ds = MockCampusDataSource()..start();
  ref.onDispose(ds.dispose);
  return ds;
});

/// 부산대 금정회관 주간 식단 (네트워크 → 캐시 → 내장 에셋 3단 폴백).
/// 내장 에셋 덕분에 웹(CORS)·오프라인에서도 항상 데이터가 있다.
final pnuMenuProvider = FutureProvider<KumjungWeekMenu>(
  (ref) => PnuMenuService().fetchWeek(),
);

/// 커스텀 Next.js API 클라이언트 (식권·웨이팅 쓰기용)
final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(Supabase.instance.client),
);

/// ── Repository (여기서 구현체 선택) ─────────────────────
final cafeteriaRepositoryProvider = Provider<CafeteriaRepository>((ref) {
  if (ref.watch(useSupabaseProvider)) {
    return SupabaseCafeteriaRepository(Supabase.instance.client);
  }
  return MockCafeteriaRepository(ref.watch(campusDataSourceProvider));
});

final ticketRepositoryProvider = Provider<TicketRepository>((ref) {
  if (ref.watch(useSupabaseProvider)) {
    return SupabaseTicketRepository(
      Supabase.instance.client,
      ref.watch(apiClientProvider),
    );
  }
  return MockTicketRepository(ref.watch(campusDataSourceProvider));
});

final restaurantRepositoryProvider = Provider<RestaurantRepository>((ref) {
  if (ref.watch(useSupabaseProvider)) {
    return SupabaseRestaurantRepository(
      Supabase.instance.client,
      ref.watch(apiClientProvider),
    );
  }
  return MockRestaurantRepository(ref.watch(campusDataSourceProvider));
});

/// AI 추천 — 우선순위: ① Gemini (키 설정 시) ② 백엔드 서버 ③ 규칙 기반 Mock.
/// ⚠️ 현재 서버 /api/ai/search 미구현 상태라 Gemini를 1순위로 둠.
///    백엔드가 구현하면 ①② 순서를 교체할 것.
/// 시연(Mock) 모드에서는 항상 ③ (오프라인 안전).
final aiRepositoryProvider = Provider<AiRepository>((ref) {
  if (ref.watch(useSupabaseProvider)) {
    if (Env.hasGemini) {
      return GeminiAiRepository(Env.geminiApiKey);
    }
    if (ref.watch(apiClientProvider).isReady) {
      return ApiAiRepository(ref.watch(apiClientProvider));
    }
  }
  return MockAiRepository();
});

/// 홈 검색바에서 입력한 질문을 AI 화면으로 전달 (소비 후 null로 초기화)
final pendingAiQuestionProvider = StateProvider<String?>((ref) => null);

/// 호출 알림 ON/OFF — 마이 탭 스위치와 연동, 앱 시작 시 main()에서
/// SharedPreferences 저장값('notify_enabled')으로 override됨.
final callAlertEnabledProvider = StateProvider<bool>((ref) => true);

/// 온보딩 완료 여부 — main()에서 저장값('onboarding_done')으로 override됨.
/// false면 라우터가 /onboarding으로 보냄.
final onboardingDoneProvider = StateProvider<bool>((ref) => false);

/// ── 화면용 스트림/퓨처 (구현체와 무관 — 변경 없음) ────────
/// 학식 라인 스트림.
/// · 부산대 공식 식단이 확보되면 메뉴·가격을 실제 값으로 덮어씀 (하드코딩 제거)
/// · 시간대 자동 전환: 17시 전 중식 / 17시 이후 석식 (학생식당 공식 운영시간 기준)
/// · Supabase 모드에서 DB에 라인이 없으면 기본 라인으로 폴백 (빈 화면 방지)
final cafeteriaLinesProvider = StreamProvider<List<CafeteriaLine>>((ref) {
  final pnuMenu = ref.watch(pnuMenuProvider).valueOrNull;
  return ref.watch(cafeteriaRepositoryProvider).watchLines().map((lines) {
    final base = lines.isEmpty ? _fallbackLines : lines;
    return _overlayRealMenus(base, pnuMenu);
  });
});

/// DB 시드 전 폴백 라인 (금정회관 실구조)
const _fallbackLines = [
  CafeteriaLine(
    id: 'line_1f_jeongsik',
    name: '1층 정식',
    location: '금정회관 1층 학생식당',
    todayMenu: ['식단 로딩 중'],
    price: 5000,
    waitingCount: 12,
  ),
  CafeteriaLine(
    id: 'line_1f_danpum',
    name: '1층 일품',
    location: '금정회관 1층 학생식당',
    todayMenu: ['식단 로딩 중'],
    price: 5000,
    waitingCount: 6,
    avgServeSecondsPerPerson: 20,
  ),
  CafeteriaLine(
    id: 'line_2f_jeongsik',
    name: '2층 교직원 정식',
    location: '금정회관 2층 교직원식당 (외부인 이용가능)',
    todayMenu: ['식단 로딩 중'],
    price: 6500,
    waitingCount: 20,
    avgServeSecondsPerPerson: 30,
  ),
];

/// 실제 식단 오버레이 — 금정회관 실구조 + 운영시간 기준:
/// · 1층 정식/일품 ← 학생식당 (17시 전 중식, 17시 이후 석식 메뉴)
/// · 2층 ← 교직원식당 중식 정식 (중식만 운영)
List<CafeteriaLine> _overlayRealMenus(
  List<CafeteriaLine> lines,
  KumjungWeekMenu? week,
) {
  if (week == null || week.days.isEmpty) return lines;

  PnuMenuSection? pick(List<PnuMenuSection>? list, String name) {
    for (final s in list ?? const <PnuMenuSection>[]) {
      if (s.name.contains(name)) return s;
    }
    return null;
  }

  // 시간대: 공식 운영시간 (중식 11:00-17:00 / 석식 17:00-18:30)
  final isDinner = DateTime.now().hour >= PnuMenuService.dinnerStartHour;

  final studentDay =
      week.todayOrLatest(where: (d) => d.studentLunch.isNotEmpty);
  final staffDay = week.todayOrLatest(where: (d) => d.staffLunch.isNotEmpty);

  final studentSections = (isDinner &&
          (studentDay?.studentDinner.isNotEmpty ?? false))
      ? studentDay!.studentDinner
      : studentDay?.studentLunch;

  final jeongsik = pick(studentSections, '정식');
  final ilpum = pick(studentSections, '일품');
  final staffJeongsik = pick(staffDay?.staffLunch, '정식');

  PnuMenuSection? sectionFor(CafeteriaLine line) {
    if (line.name.contains('단품') || line.name.contains('일품')) return ilpum;
    if (line.name.contains('2층') || line.name.contains('교직원')) {
      return staffJeongsik;
    }
    return jeongsik;
  }

  return [
    for (final line in lines)
      switch (sectionFor(line)) {
        null => line,
        final s => line.copyWith(todayMenu: s.items, price: s.price),
      },
  ];
}

final myTicketsProvider = StreamProvider<List<MealTicket>>(
  (ref) => ref.watch(ticketRepositoryProvider).watchMyTickets(),
);

final ticketProvider = StreamProvider.family<MealTicket, String>(
  (ref, ticketId) => ref.watch(ticketRepositoryProvider).watchTicket(ticketId),
);

final restaurantsProvider = StreamProvider<List<Restaurant>>(
  (ref) => ref.watch(restaurantRepositoryProvider).watchRestaurants(),
);

final myWaitingsProvider = StreamProvider<List<RemoteWaiting>>(
  (ref) => ref.watch(restaurantRepositoryProvider).watchMyWaitings(),
);

final couponsProvider = FutureProvider<List<Coupon>>(
  (ref) => ref.watch(restaurantRepositoryProvider).fetchCoupons(),
);
