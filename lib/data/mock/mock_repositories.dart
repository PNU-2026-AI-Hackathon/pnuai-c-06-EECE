import '../models/cafeteria_line.dart';
import '../models/coupon.dart';
import '../models/meal_ticket.dart';
import '../models/remote_waiting.dart';
import '../models/restaurant.dart';
import '../repositories/cafeteria_repository.dart';
import '../repositories/restaurant_repository.dart';
import '../repositories/ticket_repository.dart';
import 'mock_campus_data_source.dart';

/// Mock 구현체 3종 — 추후 Supabase 구현체로 교체 시 providers.dart만 수정.

class MockCafeteriaRepository implements CafeteriaRepository {
  MockCafeteriaRepository(this._ds);
  final MockCampusDataSource _ds;

  @override
  Stream<List<CafeteriaLine>> watchLines() => _ds.watchLines();

  @override
  Future<List<CafeteriaLine>> fetchLines() async => _ds.lines;
}

class MockTicketRepository implements TicketRepository {
  MockTicketRepository(this._ds);
  final MockCampusDataSource _ds;

  @override
  Future<MealTicket> purchaseTicket(String lineId) async {
    // 실제 결제 대신 약간의 지연으로 결제 UX 흉내
    await Future<void>.delayed(const Duration(milliseconds: 400));
    return _ds.purchaseTicket(lineId);
  }

  @override
  Stream<List<MealTicket>> watchMyTickets() => _ds.watchTickets();

  @override
  Stream<MealTicket> watchTicket(String ticketId) => _ds
      .watchTickets()
      .where((list) => list.any((t) => t.id == ticketId))
      .map((list) => list.firstWhere((t) => t.id == ticketId));

  @override
  Future<void> checkIn(String ticketId) async => _ds.checkIn(ticketId);

  @override
  Future<void> cancelTicket(String ticketId) async => _ds.cancelTicket(ticketId);
}

class MockRestaurantRepository implements RestaurantRepository {
  MockRestaurantRepository(this._ds);
  final MockCampusDataSource _ds;

  @override
  Stream<List<Restaurant>> watchRestaurants() => _ds.watchRestaurants();

  @override
  Future<List<Coupon>> fetchCoupons() async => _ds.coupons;

  @override
  Future<RemoteWaiting> joinWaiting(String restaurantId) async {
    await Future<void>.delayed(const Duration(milliseconds: 300));
    return _ds.joinWaiting(restaurantId);
  }

  @override
  Stream<List<RemoteWaiting>> watchMyWaitings() => _ds.watchWaitings();
}
