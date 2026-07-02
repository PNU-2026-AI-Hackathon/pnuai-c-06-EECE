/// 부산대 인근 제휴 식당
class Restaurant {
  final String id;
  final String name;
  final String category; // 한식, 일식 ...
  final String emoji; // MVP: 이미지 대신 이모지
  final int walkMinutes; // 정문 기준 도보
  final int waitingTeams; // 현재 대기 팀 수 (실시간)
  final String discountText; // 학생 할인 문구
  final bool waitingAvailable;

  const Restaurant({
    required this.id,
    required this.name,
    required this.category,
    required this.emoji,
    required this.walkMinutes,
    required this.waitingTeams,
    required this.discountText,
    this.waitingAvailable = true,
  });

  Restaurant copyWith({int? waitingTeams}) {
    return Restaurant(
      id: id,
      name: name,
      category: category,
      emoji: emoji,
      walkMinutes: walkMinutes,
      waitingTeams: waitingTeams ?? this.waitingTeams,
      discountText: discountText,
      waitingAvailable: waitingAvailable,
    );
  }
}
