import '../models/cafeteria_line.dart';

/// 학식 라인 데이터 소스 인터페이스.
/// 지금은 MockCafeteriaRepository, 추후 SupabaseCafeteriaRepository로 교체.
/// UI는 이 인터페이스만 알기 때문에 교체 시 화면 코드 변경 없음.
abstract class CafeteriaRepository {
  /// 라인별 실시간 대기 현황 (Mock: Timer 시뮬레이션 / 추후: Supabase Realtime)
  Stream<List<CafeteriaLine>> watchLines();

  Future<List<CafeteriaLine>> fetchLines();
}
