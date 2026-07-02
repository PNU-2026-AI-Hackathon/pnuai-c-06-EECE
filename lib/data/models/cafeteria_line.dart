/// 학식 배식 라인 (금정회관: 1층 정식 · 1층 단품 · 2층 정식)
enum LineStatus { open, closed }

/// 혼잡도 — 대기 인원 기준 3단계
enum CongestionLevel { relaxed, normal, crowded }

extension CongestionLevelX on CongestionLevel {
  String get label => switch (this) {
        CongestionLevel.relaxed => '여유',
        CongestionLevel.normal => '보통',
        CongestionLevel.crowded => '혼잡',
      };
}

class CafeteriaLine {
  final String id;
  final String name; // 예: 1층 정식
  final String location; // 예: 금정회관 1층
  final List<String> todayMenu;
  final int price;
  final int waitingCount; // 현재 대기 인원 (실시간)
  final int avgServeSecondsPerPerson; // 1인당 평균 배식 시간
  final LineStatus status;

  const CafeteriaLine({
    required this.id,
    required this.name,
    required this.location,
    required this.todayMenu,
    required this.price,
    required this.waitingCount,
    this.avgServeSecondsPerPerson = 25,
    this.status = LineStatus.open,
  });

  /// 예상 대기 시간(분)
  int get estimatedWaitMinutes =>
      (waitingCount * avgServeSecondsPerPerson / 60).ceil();

  CongestionLevel get congestion {
    if (waitingCount < 10) return CongestionLevel.relaxed;
    if (waitingCount < 25) return CongestionLevel.normal;
    return CongestionLevel.crowded;
  }

  CafeteriaLine copyWith({
    List<String>? todayMenu,
    int? waitingCount,
    LineStatus? status,
  }) {
    return CafeteriaLine(
      id: id,
      name: name,
      location: location,
      todayMenu: todayMenu ?? this.todayMenu,
      price: price,
      waitingCount: waitingCount ?? this.waitingCount,
      avgServeSecondsPerPerson: avgServeSecondsPerPerson,
      status: status ?? this.status,
    );
  }
}
