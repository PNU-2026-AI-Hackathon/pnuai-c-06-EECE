import '../models/coupon.dart';
import '../models/remote_waiting.dart';
import '../models/restaurant.dart';

/// 제휴 식당 · 원격 웨이팅 · 쿠폰 인터페이스
abstract class RestaurantRepository {
  Stream<List<Restaurant>> watchRestaurants();

  Future<List<Coupon>> fetchCoupons();

  /// 원격 웨이팅 등록 → 웨이팅 번호 발급
  Future<RemoteWaiting> joinWaiting(String restaurantId);

  /// 내 웨이팅 목록 (앞 팀 수 실시간 갱신)
  Stream<List<RemoteWaiting>> watchMyWaitings();
}
