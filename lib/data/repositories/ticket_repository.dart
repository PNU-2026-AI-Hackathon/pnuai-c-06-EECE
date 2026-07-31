import '../models/meal_ticket.dart';

/// 모바일 QR 식권 인터페이스.
/// 핵심 도메인 규칙: 식권 구매 = 해당 라인 대기열 자동 등록 (대기번호 발급)
abstract class TicketRepository {
  /// 식권 구매 → 대기번호 즉시 발급
  Future<MealTicket> purchaseTicket(String lineId);

  /// 내 식권 목록 (상태 실시간 갱신: 대기중 → 호출됨 → 사용완료)
  Stream<List<MealTicket>> watchMyTickets();

  /// 식권 1장 실시간 추적 (QR 화면용)
  Stream<MealTicket> watchTicket(String ticketId);

  /// 배식대 QR 스캔 체크인 → 대기열에서 제거
  Future<void> checkIn(String ticketId);

  /// 실수 구매 취소 — 호출 전(대기중)만 가능, 대기열에서 자동 제거
  Future<void> cancelTicket(String ticketId);
}
