import '../models/cafeteria_line.dart';
import '../repositories/ai_repository.dart';
import 'api_client.dart';

/// 서버 AI 구현 — POST /api/ai/search 호출.
/// 백엔드 배포 후 providers.dart의 스위치로 활성화됨.
class ApiAiRepository implements AiRepository {
  ApiAiRepository(this._client);

  final ApiClient _client;

  @override
  Future<AiRecommendation> ask(
    String question, {
    List<CafeteriaLine> lines = const [],
  }) async {
    final answer = await _client.aiSearch(question);
    // TODO(백엔드 확장): 응답에 lineId/restaurantId가 추가되면 함께 매핑
    return AiRecommendation(answer: answer);
  }
}
