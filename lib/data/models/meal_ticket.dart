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
  });

  /// 배식대 QR 스캔용 페이로드 (추후 서버 서명 토큰으로 교체)
  String get qrData => 'PNU-BAPMUKJA|$id|$lineId|$queueNumber';

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
    );
  }
}
