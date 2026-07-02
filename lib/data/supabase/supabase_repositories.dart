import 'package:supabase_flutter/supabase_flutter.dart';

import '../api/api_client.dart';
import '../models/cafeteria_line.dart';
import '../models/coupon.dart';
import '../models/meal_ticket.dart';
import '../models/remote_waiting.dart';
import '../models/restaurant.dart';
import '../repositories/cafeteria_repository.dart';
import '../repositories/restaurant_repository.dart';
import '../repositories/ticket_repository.dart';
import 'supabase_mappers.dart';

/// 실제 백엔드 연결 구현체 (docs/backend_contract.md 4절 확정 스키마 기준).
///  - 조회/실시간: Supabase 직접 (restaurants / dining_lines / menus / tickets / waitings / coupons)
///  - 식권 구매·웨이팅 등록(쓰기): 커스텀 Next.js API (아직 배포 전 → ApiClient가 명확히 안내)
///
/// ★ 테이블명이 다르면 아래 상수만, 컬럼명이 다르면 supabase_mappers.dart만 수정.
const _tRestaurants = 'restaurants';
const _tDiningLines = 'dining_lines';
const _tMenus = 'menus';
const _tTickets = 'tickets';
const _tWaitings = 'waitings';
const _tCoupons = 'coupons';

String _today() => DateTime.now().toIso8601String().substring(0, 10);

/// dining_lines에는 실시간 대기 인원 컬럼이 없어(4절 참고), tickets(status='paid') 개수로
/// 직접 계산한다. tickets 테이블 변화를 "심박"으로 구독해 매번 관련 테이블을 다시 조회한다.
/// (식당/라인/메뉴 등록 자체는 자주 안 바뀌는 데이터라 매번 전체 재조회해도 MVP 규모에선 무리 없음.
///  데이터가 커지면 백엔드 RPC나 /api/lines/{id}/status로 옮기는 걸 권장)
class SupabaseCafeteriaRepository implements CafeteriaRepository {
  SupabaseCafeteriaRepository(this._client);
  final SupabaseClient _client;

  @override
  Stream<List<CafeteriaLine>> watchLines() =>
      _client.from(_tTickets).stream(primaryKey: ['id']).asyncMap((_) => fetchLines());

  @override
  Future<List<CafeteriaLine>> fetchLines() async {
    final lines = await _client.from(_tDiningLines).select().order('name');
    final restaurants = await _client.from(_tRestaurants).select();
    final menuRows = await _client.from(_tMenus).select().eq('menu_date', _today());
    final paidTickets = await _client.from(_tTickets).select().eq('status', 'paid');

    final restaurantById = <String, Map<String, dynamic>>{
      for (final r in restaurants) r['id'].toString(): r,
    };

    final waitingCountByLine = <String, int>{};
    for (final t in paidTickets) {
      final lineId = t['dining_line_id']?.toString();
      if (lineId == null) continue;
      waitingCountByLine[lineId] = (waitingCountByLine[lineId] ?? 0) + 1;
    }

    return lines.map((line) {
      final lineId = line['id'].toString();
      final restId = SupabaseMappers.restaurantIdOfLine(line);
      final rest = restaurantById[restId];

      final matchedMenus =
          menuRows.where((m) => m['restaurant_id']?.toString() == restId).toList();

      return SupabaseMappers.line(
        line,
        restaurantName: (rest?['name'] as String?) ?? '',
        waitingCount: waitingCountByLine[lineId] ?? 0,
        menu: matchedMenus.map(SupabaseMappers.menuName).toList(),
        price: matchedMenus.isEmpty ? 0 : SupabaseMappers.menuPrice(matchedMenus.first),
      );
    }).toList();
  }
}

/// restaurants에도 실시간 대기 팀 수 컬럼이 없어, waitings(status='waiting') 개수로 계산한다.
/// waitings 테이블 변화를 심박으로 구독.
class SupabaseRestaurantRepository implements RestaurantRepository {
  SupabaseRestaurantRepository(this._client, this._api);
  final SupabaseClient _client;
  final ApiClient _api;

  @override
  Stream<List<Restaurant>> watchRestaurants() => _client
      .from(_tWaitings)
      .stream(primaryKey: ['id'])
      .asyncMap((_) => _fetchRestaurants());

  Future<List<Restaurant>> _fetchRestaurants() async {
    final restaurants = await _client.from(_tRestaurants).select();
    final activeWaitings = await _client.from(_tWaitings).select().eq('status', 'waiting');

    final teamsByRestaurant = <String, int>{};
    for (final w in activeWaitings) {
      final restId = w['restaurant_id']?.toString();
      if (restId == null) continue;
      teamsByRestaurant[restId] = (teamsByRestaurant[restId] ?? 0) + 1;
    }

    return restaurants
        .map((r) => SupabaseMappers.restaurant(
              r,
              waitingTeams: teamsByRestaurant[r['id'].toString()] ?? 0,
            ))
        .toList();
  }

  @override
  Future<List<Coupon>> fetchCoupons() async {
    final rows = await _client.from(_tCoupons).select();
    return rows.map(SupabaseMappers.coupon).toList();
  }

  // 쓰기 = 커스텀 API (배포 전까지 ApiClient가 안내 예외 던짐)
  @override
  Future<RemoteWaiting> joinWaiting(String restaurantId) =>
      _api.joinWaiting(restaurantId);

  @override
  Stream<List<RemoteWaiting>> watchMyWaitings() {
    final uid = _client.auth.currentUser?.id;
    if (uid == null) return Stream.value(const <RemoteWaiting>[]);
    return _client
        .from(_tWaitings)
        .stream(primaryKey: ['id'])
        .eq('user_id', uid)
        .asyncMap(_toRemoteWaitings);
  }

  Future<List<RemoteWaiting>> _toRemoteWaitings(List<Map<String, dynamic>> rows) async {
    // done/canceled는 진행 중 목록에 안 보여줌
    final active = rows.where((w) {
      final s = w['status'] as String?;
      return s == 'waiting' || s == 'called';
    }).toList();
    if (active.isEmpty) return const [];

    final restaurants = await _client.from(_tRestaurants).select();
    final restaurantById = <String, Map<String, dynamic>>{
      for (final r in restaurants) r['id'].toString(): r,
    };
    final waitingRows = await _client.from(_tWaitings).select().eq('status', 'waiting');

    return active.map((w) {
      final restId = w['restaurant_id']?.toString() ?? '';
      final myQueueNo = (w['queue_no'] as num?)?.toInt() ?? 0;
      final teamsAhead = w['status'] == 'waiting'
          ? waitingRows.where((x) {
              return x['restaurant_id']?.toString() == restId &&
                  ((x['queue_no'] as num?)?.toInt() ?? 0) < myQueueNo;
            }).length
          : 0;
      return RemoteWaiting(
        id: w['id'].toString(),
        restaurantId: restId,
        restaurantName: (restaurantById[restId]?['name'] as String?) ?? '',
        number: myQueueNo,
        teamsAhead: teamsAhead,
        status: SupabaseMappers.waitingStatus(w['status'] as String?),
        joinedAt: DateTime.tryParse(w['created_at']?.toString() ?? '') ?? DateTime.now(),
      );
    }).toList();
  }
}

class SupabaseTicketRepository implements TicketRepository {
  SupabaseTicketRepository(this._client, this._api);
  final SupabaseClient _client;
  final ApiClient _api;

  @override
  Future<MealTicket> purchaseTicket(String lineId) => _api.purchaseTicket(lineId);

  @override
  Future<void> checkIn(String ticketId) => _api.verifyTicket(ticketId);

  @override
  Stream<List<MealTicket>> watchMyTickets() {
    final uid = _client.auth.currentUser?.id;
    if (uid == null) return Stream.value(const <MealTicket>[]);
    return _client
        .from(_tTickets)
        .stream(primaryKey: ['id'])
        .eq('user_id', uid)
        .asyncMap(_toMealTickets);
  }

  @override
  Stream<MealTicket> watchTicket(String ticketId) => _client
      .from(_tTickets)
      .stream(primaryKey: ['id'])
      .eq('id', ticketId)
      .asyncMap(_toMealTickets)
      .where((tickets) => tickets.isNotEmpty)
      .map((tickets) => tickets.first);

  Future<List<MealTicket>> _toMealTickets(List<Map<String, dynamic>> rows) async {
    if (rows.isEmpty) return const [];

    final lines = await _client.from(_tDiningLines).select();
    final lineById = <String, Map<String, dynamic>>{
      for (final l in lines) l['id'].toString(): l,
    };
    final menuRows = await _client.from(_tMenus).select().eq('menu_date', _today());

    // 대기번호는 같은 라인 내 status='paid' 티켓을 paid_at 순으로 정렬한 순번으로 계산.
    final paidTickets = await _client.from(_tTickets).select().eq('status', 'paid');
    paidTickets.sort((a, b) =>
        (a['paid_at']?.toString() ?? '').compareTo(b['paid_at']?.toString() ?? ''));
    final queueByLine = <String, List<String>>{};
    for (final t in paidTickets) {
      final lineId = t['dining_line_id']?.toString() ?? '';
      (queueByLine[lineId] ??= []).add(t['id'].toString());
    }

    return rows.map((t) {
      final id = t['id'].toString();
      final lineId = t['dining_line_id']?.toString() ?? '';
      final line = lineById[lineId];
      final restId = line?['restaurant_id']?.toString();
      Map<String, dynamic>? menu;
      for (final m in menuRows) {
        if (m['restaurant_id']?.toString() == restId) {
          menu = m;
          break;
        }
      }
      final queue = queueByLine[lineId] ?? const <String>[];
      final rank = queue.indexOf(id); // -1이면 paid 상태 아님(used/expired)

      return MealTicket(
        id: id,
        lineId: lineId,
        lineName: (line?['name'] as String?) ?? '',
        menuName: menu != null ? SupabaseMappers.menuName(menu) : '',
        price: menu != null ? SupabaseMappers.menuPrice(menu) : 0,
        queueNumber: rank >= 0 ? rank + 1 : 0,
        aheadCount: rank >= 0 ? rank : 0,
        status: SupabaseMappers.ticketStatus(t['status'] as String?),
        purchasedAt:
            DateTime.tryParse(t['paid_at']?.toString() ?? '') ?? DateTime.now(),
        qrToken: t['qr_token']?.toString(),
      );
    }).toList();
  }
}
