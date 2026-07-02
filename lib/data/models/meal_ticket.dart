/// 모바일 QR 식권 — 구매 즉시 대기열 등록 (계획서 2.3 "앱이 곧 데이터다")
enum TicketStatus { waiting, called, used }

extension TicketStatusX on TicketStatus {
  String get label => switch (this) {
        TicketStatus.waiting => '대기중',
        TicketStatus.called => '호출됨',
        TicketStatus.used => '사용완료',
      };
}

class MealTicket {
  final String id;
  final String lineId;
  final String lineName;
  final String menuName;
  final int price;
  final int queueNumber; // 대기번호
  final int aheadCount; // 내 앞 대기 인원 (실시간 갱신)
  final TicketStatus status;
  final DateTime purchasedAt;
  final String? qrToken; // 서버 발급 검증 토큰(POST /api/tickets 응답). 없으면(Mock) 로컬 값으로 대체.

  const MealTicket({
    required this.id,
    required this.lineId,
    required this.lineName,
    required this.menuName,
    required this.price,
    required this.queueNumber,
    required this.aheadCount,
    required this.status,
    required this.purchasedAt,
    this.qrToken,
  });

  /// 배식대 QR 스캔용 페이로드. 서버 qrToken이 있으면 그걸 그대로 사용(검증 대상과 일치해야 함).
  String get qrData => qrToken ?? 'PNU-BAPMUKJA|$id|$lineId|$queueNumber';

  MealTicket copyWith({int? aheadCount, TicketStatus? status}) {
    return MealTicket(
      id: id,
      lineId: lineId,
      lineName: lineName,
      menuName: menuName,
      price: price,
      queueNumber: queueNumber,
      aheadCount: aheadCount ?? this.aheadCount,
      status: status ?? this.status,
      purchasedAt: purchasedAt,
      qrToken: qrToken,
    );
  }
}
