import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/mock/mock_campus_data_source.dart';
import '../data/mock/mock_repositories.dart';
import '../data/models/cafeteria_line.dart';
import '../data/models/coupon.dart';
import '../data/models/meal_ticket.dart';
import '../data/models/remote_waiting.dart';
import '../data/models/restaurant.dart';
import '../data/repositories/cafeteria_repository.dart';
import '../data/repositories/restaurant_repository.dart';
import '../data/repositories/ticket_repository.dart';

/// ── 데이터 소스 ──────────────────────────────────────
/// Supabase 연동 시: 아래 repository provider 3개의 구현체만 교체하면 끝.
final campusDataSourceProvider = Provider<MockCampusDataSource>((ref) {
  final ds = MockCampusDataSource()..start();
  ref.onDispose(ds.dispose);
  return ds;
});

/// ── Repository ──────────────────────────────────────
final cafeteriaRepositoryProvider = Provider<CafeteriaRepository>(
  (ref) => MockCafeteriaRepository(ref.watch(campusDataSourceProvider)),
);

final ticketRepositoryProvider = Provider<TicketRepository>(
  (ref) => MockTicketRepository(ref.watch(campusDataSourceProvider)),
);

final restaurantRepositoryProvider = Provider<RestaurantRepository>(
  (ref) => MockRestaurantRepository(ref.watch(campusDataSourceProvider)),
);

/// ── 화면용 스트림/퓨처 ────────────────────────────────
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
