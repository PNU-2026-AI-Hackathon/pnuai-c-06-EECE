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

/// AI 추천 — 우선순위: ① 백엔드 서버(/api/ai/search, 배포 시)
/// ② Gemini 무료 API (GEMINI_API_KEY 설정 시) ③ 규칙 기반 Mock.
/// 시연(Mock) 모드에서는 항상 ③ (오프라인 안전).
final aiRepositoryProvider = Provider<AiRepository>((ref) {
  if (ref.watch(useSupabaseProvider)) {
    if (ref.watch(apiClientProvider).isReady) {
      return ApiAiRepository(ref.watch(apiClientProvider));
    }
    if (Env.hasGemini) {
      return GeminiAiRepository(Env.geminiApiKey);
    }
  }
  return MockAiRepository();
});

/// 홈 검색바에서 입력한 질문을 AI 화면으로 전달 (소비 후 null로 초기화)
final pendingAiQuestionProvider = StateProvider<String?>((ref) => null);

/// 호출 알림 ON/OFF — 마이 탭 스위치와 연동, 앱 시작 시 main()에서
/// SharedPreferences 저장값('notify_enabled')으로 override됨.
final callAlertEnabledProvider = StateProvider<bool>((ref) => true);

/// ── 화면용 스트림/퓨처 (구현체와 무관 — 변경 없음) ────────
final cafeteriaLinesProvider = StreamProvider<List<CafeteriaLine>>(
  (ref) => ref.watch(cafeteriaRepositoryProvider).watchLines(),
);

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
