import '../models/cafeteria_line.dart';

/// AI 추천 결과 — answer는 필수, 추천 대상 ID는 있으면 화면 이동에 사용
class AiRecommendation {
  final String answer;
  final String? lineId; // 추천 학식 라인 (탭하면 홈/구매로 연결)
  final String? restaurantId; // 추천 제휴식당

  const AiRecommendation({
    required this.answer,
    this.lineId,
    this.restaurantId,
  });
}

/// AI 메뉴 추천 계약 — 백엔드는 이 인터페이스만 구현하면 됨.
///
/// 서버 계약: POST /api/ai/search {query} → {answer, menus[, lineId, restaurantId]}
/// (docs/backend_contract.md 3절, docs/backend_handoff.md 참고)
abstract interface class AiRepository {
  /// 자연어 질문 + 현재 대기 현황 → 추천 답변.
  /// [lines]는 실시간 혼잡도 컨텍스트 (서버 구현은 무시해도 됨 — 서버가 직접 조회 가능).
  Future<AiRecommendation> ask(
    String question, {
    List<CafeteriaLine> lines = const [],
  });
}
