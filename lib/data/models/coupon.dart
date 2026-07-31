/// 학생 할인 쿠폰 (학번 인증 기반 — 락인 전략)
class Coupon {
  final String id;
  final String restaurantName;
  final String title; // 예: 아메리카노 1+1
  final String condition; // 예: 학생증 제시
  final String expiresText; // 예: ~7/31

  const Coupon({
    required this.id,
    required this.restaurantName,
    required this.title,
    required this.condition,
    required this.expiresText,
  });
}
