/// 제휴 식당 원격 웨이팅
enum WaitingStatus { waiting, called }

extension WaitingStatusX on WaitingStatus {
  String get label => switch (this) {
        WaitingStatus.waiting => '대기중',
        WaitingStatus.called => '입장 호출!',
      };
}

class RemoteWaiting {
  final String id;
  final String restaurantId;
  final String restaurantName;
  final int number; // 웨이팅 번호
  final int teamsAhead; // 내 앞 팀 수 (실시간)
  final WaitingStatus status;
  final DateTime joinedAt;

  const RemoteWaiting({
    required this.id,
    required this.restaurantId,
    required this.restaurantName,
    required this.number,
    required this.teamsAhead,
    required this.status,
    required this.joinedAt,
  });

  RemoteWaiting copyWith({int? teamsAhead, WaitingStatus? status}) {
    return RemoteWaiting(
      id: id,
      restaurantId: restaurantId,
      restaurantName: restaurantName,
      number: number,
      teamsAhead: teamsAhead ?? this.teamsAhead,
      status: status ?? this.status,
      joinedAt: joinedAt,
    );
  }
}
