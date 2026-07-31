import '../models/cafeteria_line.dart';
import '../repositories/ai_repository.dart';

/// 규칙 기반 Mock AI — 기존 ai_screen 내장 로직을 이동.
/// 서버(/api/ai/search) 배포 전까지 사용, 시연 폴백용으로도 유지.
class MockAiRepository implements AiRepository {
  @override
  Future<AiRecommendation> ask(
    String question, {
    List<CafeteriaLine> lines = const [],
    List<AiChatTurn> history = const [], // 규칙 기반이라 맥락 미사용
  }) async {
    // 챗봇 응답 느낌을 위한 지연
    await Future.delayed(const Duration(milliseconds: 400));

    if (lines.isEmpty) {
      return const AiRecommendation(
        answer: '대기 데이터를 불러오는 중이에요. 잠시 후 다시 시도해 주세요.',
      );
    }

    // 규칙 1: 키워드로 메뉴 매칭 (예: "매운", "치킨")
    final keywords = ['매운', '맵', '치킨', '돈까스', '국', '김치', '두부', '제육'];
    for (final k in keywords) {
      if (!question.contains(k)) continue;
      for (final line in lines) {
        final hit = line.todayMenu.where((m) => m.contains(k.replaceAll('맵', '매')));
        if (hit.isNotEmpty) {
          return AiRecommendation(
            answer: '"${hit.first}" 어때요? ${line.name}에서 먹을 수 있어요. '
                '지금 대기 ${line.waitingCount}명, 약 ${line.estimatedWaitMinutes}분 예상이에요.'
                '\n\n(MVP Mock 응답 — 서버 /api/ai/search 배포 시 자동 교체)',
            lineId: line.id,
          );
        }
      }
    }

    // 규칙 2: 기본 — 최소 대기 라인 추천
    final fastest = [...lines]
      ..sort((a, b) => a.estimatedWaitMinutes.compareTo(b.estimatedWaitMinutes));
    final best = fastest.first;
    return AiRecommendation(
      answer: '지금은 "${best.name}"이 가장 빨라요! '
          '대기 ${best.waitingCount}명, 약 ${best.estimatedWaitMinutes}분 예상이에요. '
          '오늘 메뉴는 ${best.todayMenu.join(", ")}입니다.'
          '\n\n(MVP Mock 응답 — 서버 /api/ai/search 배포 시 자동 교체)',
      lineId: best.id,
    );
  }
}
