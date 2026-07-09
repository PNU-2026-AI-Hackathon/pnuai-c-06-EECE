import 'dart:async';
import 'dart:math';

import '../models/cafeteria_line.dart';
import '../models/coupon.dart';
import '../models/meal_ticket.dart';
import '../models/remote_waiting.dart';
import '../models/restaurant.dart';

/// Mock 캠퍼스 데이터 소스 + 실시간 대기열 시뮬레이터.
///
/// [tickInterval]마다:
///  - 학식 라인: 도착 0~3명 / 배식 1~3명 랜덤 → 대기 인원 변동
///  - 식권: 배식 진행에 따라 내 앞 대기 감소, 0명이면 '호출됨'
///  - 제휴 식당: 대기 팀 수 변동, 내 웨이팅 앞 팀 감소 → 0이면 '입장 호출'
///
/// Supabase 연동 시 이 클래스만 폐기하면 된다.
class MockCampusDataSource {
  MockCampusDataSource({this.tickInterval = const Duration(seconds: 4)});

  final Duration tickInterval;
  final _random = Random();
  Timer? _timer;

  // ── 학식 라인 (금정회관 실구조: 1층 학생식당 정식·일품 / 2층 교직원식당) ──
  // 메뉴·가격은 부산대 공식 식단안내 기준 (pnuMenuProvider가 최신으로 덮어씀)
  final Map<String, CafeteriaLine> _lines = {
    'line_1f_jeongsik': const CafeteriaLine(
      id: 'line_1f_jeongsik',
      name: '1층 정식',
      location: '금정회관 1층 학생식당',
      todayMenu: ['김치콩나물국', '도쿄멘치가스/소스', '마파두부', '열무겉절이', '배추김치'],
      price: 5000,
      waitingCount: 18,
    ),
    'line_1f_danpum': const CafeteriaLine(
      id: 'line_1f_danpum',
      name: '1층 일품',
      location: '금정회관 1층 학생식당',
      todayMenu: ['삼겹살버섯덮밥', '애플파이', '배추김치'],
      price: 5000,
      waitingCount: 7,
      avgServeSecondsPerPerson: 20,
    ),
    'line_2f_jeongsik': const CafeteriaLine(
      id: 'line_2f_jeongsik',
      name: '2층 교직원 정식',
      location: '금정회관 2층 교직원식당 (외부인 이용가능)',
      todayMenu: ['흑미밥', '육개장', '도톰함박스테이크/치즈', '스파게티/토마토소스', '비빔야채만두', '콩나물냉채', '김치/후식'],
      price: 6500,
      waitingCount: 26,
      avgServeSecondsPerPerson: 30,
    ),
  };

  /// 라인별 현재 배식 중인 대기번호
  final Map<String, int> _currentServing = {
    'line_1f_jeongsik': 130,
    'line_1f_danpum': 210,
    'line_2f_jeongsik': 95,
  };

  /// 라인별 다음 발급 대기번호 (= 현재 배식 번호 + 대기 인원 + 1로 시드)
  late final Map<String, int> _nextQueueNumber = {
    for (final e in _lines.entries)
      e.key: _currentServing[e.key]! + e.value.waitingCount + 1,
  };

  // ── 내 식권 ──────────────────────────────────────────
  final Map<String, MealTicket> _tickets = {};
  int _ticketSeq = 0;

  // ── 제휴 식당 ────────────────────────────────────────
  final Map<String, Restaurant> _restaurants = {
    'rest_donkatsu': const Restaurant(
      id: 'rest_donkatsu',
      name: '부대앞 왕돈까스',
      category: '일식',
      emoji: '🍱',
      walkMinutes: 5,
      waitingTeams: 4,
      discountText: '학생 인증 시 1,000원 할인',
    ),
    'rest_mara': const Restaurant(
      id: 'rest_mara',
      name: '온천장 마라탕',
      category: '중식',
      emoji: '🌶️',
      walkMinutes: 7,
      waitingTeams: 2,
      discountText: '단과대 쿠폰 — 꿔바로우 30% 할인',
    ),
    'rest_pasta': const Restaurant(
      id: 'rest_pasta',
      name: '명륜 파스타집',
      category: '양식',
      emoji: '🍝',
      walkMinutes: 10,
      waitingTeams: 6,
      discountText: '평일 점심 학생 세트 6,900원',
    ),
    'rest_bunsik': const Restaurant(
      id: 'rest_bunsik',
      name: 'NC백화점 분식당',
      category: '분식',
      emoji: '🥟',
      walkMinutes: 3,
      waitingTeams: 0,
      discountText: '앱 쿠폰 — 튀김 2개 서비스',
    ),
  };

  final List<Coupon> _coupons = const [
    Coupon(
      id: 'coupon_1',
      restaurantName: '부대앞 왕돈까스',
      title: '치즈돈까스 1,000원 할인',
      condition: '학번 인증 회원',
      expiresText: '~7/31',
    ),
    Coupon(
      id: 'coupon_2',
      restaurantName: '온천장 마라탕',
      title: '꿔바로우 30% 할인',
      condition: '공대 단과대 제휴',
      expiresText: '~8/15',
    ),
    Coupon(
      id: 'coupon_3',
      restaurantName: '명륜 파스타집',
      title: '음료 1+1',
      condition: '2인 이상 방문',
      expiresText: '~7/20',
    ),
  ];

  // ── 내 원격 웨이팅 ───────────────────────────────────
  final Map<String, RemoteWaiting> _waitings = {};
  int _waitingSeq = 0;

  // ── 스트림 ───────────────────────────────────────────
  final _linesController =
      StreamController<List<CafeteriaLine>>.broadcast();
  final _ticketsController =
      StreamController<List<MealTicket>>.broadcast();
  final _restaurantsController =
      StreamController<List<Restaurant>>.broadcast();
  final _waitingsController =
      StreamController<List<RemoteWaiting>>.broadcast();

  List<CafeteriaLine> get lines => _lines.values.toList();
  List<MealTicket> get tickets =>
      _tickets.values.toList()..sort((a, b) => b.purchasedAt.compareTo(a.purchasedAt));
  List<Restaurant> get restaurants => _restaurants.values.toList();
  List<Coupon> get coupons => _coupons;
  List<RemoteWaiting> get waitings => _waitings.values.toList();

  /// 현재 값 즉시 방출 + 이후 변경 구독 (BehaviorSubject 대용)
  Stream<List<CafeteriaLine>> watchLines() async* {
    yield lines;
    yield* _linesController.stream;
  }

  Stream<List<MealTicket>> watchTickets() async* {
    yield tickets;
    yield* _ticketsController.stream;
  }

  Stream<List<Restaurant>> watchRestaurants() async* {
    yield restaurants;
    yield* _restaurantsController.stream;
  }

  Stream<List<RemoteWaiting>> watchWaitings() async* {
    yield waitings;
    yield* _waitingsController.stream;
  }

  // ── 시뮬레이터 ───────────────────────────────────────
  void start() {
    _timer ??= Timer.periodic(tickInterval, (_) => _tick());
  }

  void dispose() {
    _timer?.cancel();
    _linesController.close();
    _ticketsController.close();
    _restaurantsController.close();
    _waitingsController.close();
  }

  void _tick() {
    // 1) 학식 라인: 도착/배식 랜덤 워크
    for (final id in _lines.keys) {
      final line = _lines[id]!;
      if (line.status == LineStatus.closed) continue;
      final arrivals = _random.nextInt(4); // 0~3명 도착
      final served = min(line.waitingCount, 1 + _random.nextInt(3)); // 1~3명 배식
      _currentServing[id] = _currentServing[id]! + served;
      _lines[id] = line.copyWith(
        waitingCount: max(0, line.waitingCount + arrivals - served),
      );
    }

    // 2) 식권: 내 앞 대기 갱신 → 0명이면 호출
    _tickets.updateAll((id, t) {
      if (t.status == TicketStatus.used) return t;
      final serving = _currentServing[t.lineId] ?? 0;
      final ahead = max(0, t.queueNumber - serving - 1);
      return t.copyWith(
        aheadCount: ahead,
        status: ahead == 0 ? TicketStatus.called : TicketStatus.waiting,
      );
    });

    // 3) 제휴 식당: 대기 팀 랜덤 워크
    for (final id in _restaurants.keys) {
      final r = _restaurants[id]!;
      final delta = _random.nextInt(3) - 1; // -1 ~ +1
      _restaurants[id] = r.copyWith(waitingTeams: max(0, r.waitingTeams + delta));
    }

    // 4) 내 웨이팅: 앞 팀 감소 → 0이면 입장 호출
    _waitings.updateAll((id, w) {
      if (w.status == WaitingStatus.called) return w;
      final ahead = max(0, w.teamsAhead - _random.nextInt(2)); // 0~1팀 입장
      return w.copyWith(
        teamsAhead: ahead,
        status: ahead == 0 ? WaitingStatus.called : WaitingStatus.waiting,
      );
    });

    _emitAll();
  }

  void _emitAll() {
    _linesController.add(lines);
    _ticketsController.add(tickets);
    _restaurantsController.add(restaurants);
    _waitingsController.add(waitings);
  }

  // ── 액션 ─────────────────────────────────────────────

  /// 식권 구매 = 대기열 자동 등록 (핵심 도메인 규칙)
  MealTicket purchaseTicket(String lineId) {
    final line = _lines[lineId];
    if (line == null) {
      throw ArgumentError('존재하지 않는 라인: $lineId');
    }
    final queueNumber = _nextQueueNumber[lineId]!;
    _nextQueueNumber[lineId] = queueNumber + 1;

    final serving = _currentServing[lineId]!;
    final ticket = MealTicket(
      id: 'ticket_${++_ticketSeq}',
      lineId: lineId,
      lineName: line.name,
      menuName: line.todayMenu.first,
      price: line.price,
      queueNumber: queueNumber,
      aheadCount: max(0, queueNumber - serving - 1),
      status: TicketStatus.waiting,
      purchasedAt: DateTime.now(),
    );
    _tickets[ticket.id] = ticket;

    // 구매 = 대기열 +1
    _lines[lineId] = line.copyWith(waitingCount: line.waitingCount + 1);
    _emitAll();
    return ticket;
  }

  /// 배식대 QR 체크인 = 대기열 제거
  void checkIn(String ticketId) {
    final t = _tickets[ticketId];
    if (t == null || t.status == TicketStatus.used) return;
    _tickets[ticketId] = t.copyWith(status: TicketStatus.used, aheadCount: 0);
    final line = _lines[t.lineId];
    if (line != null) {
      _lines[t.lineId] = line.copyWith(waitingCount: max(0, line.waitingCount - 1));
    }
    _emitAll();
  }

  /// 원격 웨이팅 등록
  RemoteWaiting joinWaiting(String restaurantId) {
    final r = _restaurants[restaurantId];
    if (r == null) {
      throw ArgumentError('존재하지 않는 식당: $restaurantId');
    }
    final waiting = RemoteWaiting(
      id: 'waiting_${++_waitingSeq}',
      restaurantId: restaurantId,
      restaurantName: r.name,
      number: 20 + _waitingSeq + _random.nextInt(10),
      teamsAhead: r.waitingTeams,
      status: r.waitingTeams == 0 ? WaitingStatus.called : WaitingStatus.waiting,
      joinedAt: DateTime.now(),
    );
    _waitings[waiting.id] = waiting;
    _restaurants[restaurantId] = r.copyWith(waitingTeams: r.waitingTeams + 1);
    _emitAll();
    return waiting;
  }
}
