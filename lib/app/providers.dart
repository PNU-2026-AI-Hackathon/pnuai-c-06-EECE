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
import '../data/repositories/cafeteria_repository.dart';
import '../data/repositories/restaurant_repository.dart';
import '../data/repositories/ticket_repository.dart';
import '../data/supabase/supabase_repositories.dart';

/// ── 데이터소스 전환 스위치 ──────────────────────────────
/// Env.useSupabase(URL·키가 채워졌는지)에 따라 Mock ↔ Supabase 자동 전환.
/// 강제로 Mock을 쓰고 싶으면 아래 값을 false로 두면 된다.
final _useSupabase = Env.useSupabase;

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
  if (_useSupabase) {
    return SupabaseCafeteriaRepository(Supabase.instance.client);
  }
  return MockCafeteriaRepository(ref.watch(campusDataSourceProvider));
});

final ticketRepositoryProvider = Provider<TicketRepository>((ref) {
  if (_useSupabase) {
    return SupabaseTicketRepository(
      Supabase.instance.client,
      ref.watch(apiClientProvider),
    );
  }
  return MockTicketRepository(ref.watch(campusDataSourceProvider));
});

final restaurantRepositoryProvider = Provider<RestaurantRepository>((ref) {
  if (_useSupabase) {
    return SupabaseRestaurantRepository(
      Supabase.instance.client,
      ref.watch(apiClientProvider),
    );
  }
  return MockRestaurantRepository(ref.watch(campusDataSourceProvider));
});

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
