import '../models/cafeteria_line.dart';
import '../models/coupon.dart';
import '../models/meal_ticket.dart';
import '../models/remote_waiting.dart';
import '../models/restaurant.dart';

/// DB row(Map) → 앱 모델 변환. 실제 스키마 기준(백엔드 조우진 제공, docs/backend_contract.md 4절 확정).
///
/// ★★ 실제 컬럼명이 다르면 이 파일의 문자열만 고치면 된다. ★★
///    (repository·화면 코드는 손대지 않아도 됨)
class SupabaseMappers {
  // ── dining_lines → CafeteriaLine ──────────────────────
  // 확정 컬럼: id, restaurant_id, name, avg_service_sec
  // waiting_count에 해당하는 컬럼이 없음 → tickets(status='paid') 개수를 세서 주입.
  // location에 해당하는 컬럼도 없음 → 소속 restaurants.name을 넣음.
  // status(운영중/마감) 컬럼도 없음 → 항상 open으로 취급(추후 컬럼 생기면 여기만 수정).
  static CafeteriaLine line(
    Map<String, dynamic> r, {
    required String restaurantName,
    required int waitingCount,
    List<String> menu = const [],
    int price = 0,
  }) {
    final avgServiceSec = (r['avg_service_sec'] as num?)?.toInt() ?? 25;
    return CafeteriaLine(
      id: r['id'].toString(),
      name: (r['name'] as String?) ?? '',
      location: restaurantName,
      todayMenu: menu,
      price: price,
      waitingCount: waitingCount,
      avgServeSecondsPerPerson: avgServiceSec,
      status: LineStatus.open,
    );
  }

  static String? restaurantIdOfLine(Map<String, dynamic> r) =>
      r['restaurant_id']?.toString();

  // ── menus → 메뉴명 문자열 ──────────────────────────────
  // 확정 컬럼: id, restaurant_id, name, price, description, menu_date
  // (식당 단위 — dining_line_id 없음. 한 식당의 오늘 메뉴를 모든 라인에 동일하게 붙임)
  static String menuName(Map<String, dynamic> r) => (r['name'] as String?) ?? '';

  static int menuPrice(Map<String, dynamic> r) => (r['price'] as num?)?.toInt() ?? 0;

  // ── restaurants → Restaurant ──────────────────────────
  // 확정 컬럼: id, type('campus'|'partner'), name, college_benefit, price_range,
  //           operating_hours(jsonb), is_waiting_available, created_at
  //
  // ⚠️ 앱 모델(category/emoji/walkMinutes/discountText)에 정확히 대응하는 컬럼이
  //    스키마에 없어 아래처럼 근사치로 채움:
  //    - category  ← type을 '학식'/'제휴'로 표시 (실제 한식/일식 등 세부 카테고리 컬럼 없음)
  //    - emoji     ← type 기반 고정 이모지 (컬럼 없음)
  //    - walkMinutes ← 컬럼 없어 0 고정 (도보 거리 계산 근거 없음)
  //    - discountText ← college_benefit이 있으면 "○○ 대상 혜택" 문구로 변환
  static Restaurant restaurant(
    Map<String, dynamic> r, {
    int waitingTeams = 0,
  }) {
    final type = (r['type'] as String?) ?? 'campus';
    final benefit = (r['college_benefit'] as String?) ?? '';
    return Restaurant(
      id: r['id'].toString(),
      name: (r['name'] as String?) ?? '',
      category: type == 'partner' ? '제휴' : '학식',
      emoji: type == 'partner' ? '🍽️' : '🍚',
      walkMinutes: 0,
      waitingTeams: waitingTeams,
      discountText: benefit.isEmpty ? '' : '$benefit 대상 혜택',
      waitingAvailable: (r['is_waiting_available'] as bool?) ?? true,
    );
  }

  // ── coupons → Coupon (확정 컬럼: id, college, title, discount, valid_until) ──
  static Coupon coupon(Map<String, dynamic> r) {
    final discount = (r['discount'] as String?) ?? '';
    final title = (r['title'] as String?) ?? '';
    return Coupon(
      id: r['id'].toString(),
      restaurantName: (r['college'] as String?) ?? '전체', // 대상 단과대
      title: discount.isEmpty ? title : '$title ($discount)',
      condition: (r['college'] as String?) != null
          ? '${r['college']} 대상'
          : '학생 인증',
      expiresText: r['valid_until'] == null
          ? ''
          : '~${r['valid_until'].toString().substring(0, 10)}',
    );
  }

  // ── tickets → TicketStatus (status = 'paid'|'called'|'used'|'expired') ──
  // 'called' = 배식대 호출됨 (2026-07-15 백엔드 verify→called 전이 배포로 활성화).
  // 'expired'는 앱에 별도 상태가 없어 'used'(비활성)로 합쳐서 표시.
  static TicketStatus ticketStatus(String? dbStatus) => switch (dbStatus) {
        'paid' => TicketStatus.waiting,
        'called' => TicketStatus.called,
        _ => TicketStatus.used, // 'used' | 'expired' | null
      };

  // ── waitings → WaitingStatus (확정 컬럼: status = 'waiting'|'called'|'done'|'canceled') ──
  static WaitingStatus waitingStatus(String? dbStatus) => switch (dbStatus) {
        'called' => WaitingStatus.called,
        _ => WaitingStatus.waiting,
      };
}
