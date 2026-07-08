import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../core/formatters.dart';
import '../models/cafeteria_line.dart';
import '../repositories/ai_repository.dart';

/// Google Gemini 무료 API 기반 AI 추천.
///
/// - 무료 티어: 카드 등록 불필요, 일 1,500회 (2026-07 기준, gemini-2.5-flash)
/// - 키 발급: https://aistudio.google.com → Get API key
/// - 실행: flutter run --dart-define=GEMINI_API_KEY=AIza...
/// - 실시간 대기 현황을 프롬프트 컨텍스트로 넣어, 답변이 현재 혼잡도를 반영함.
///
/// ⚠️ 키를 앱에 내장하는 방식은 해커톤 MVP용. 정식 배포 시에는 백엔드
///    /api/ai/search 뒤로 숨길 것 (providers.dart에서 서버 우선으로 전환됨).
class GeminiAiRepository implements AiRepository {
  GeminiAiRepository(this._apiKey);

  final String _apiKey;

  static const _model = 'gemini-2.5-flash';
  static const _endpoint =
      'https://generativelanguage.googleapis.com/v1beta/models';

  @override
  Future<AiRecommendation> ask(
    String question, {
    List<CafeteriaLine> lines = const [],
  }) async {
    final context = lines
        .map((l) => '- id:"${l.id}" | ${l.name} | 대기 ${l.waitingCount}명 '
            '(약 ${l.estimatedWaitMinutes}분, ${l.congestion.label}) | '
            '${won(l.price)} | 오늘 메뉴: ${l.todayMenu.join(', ')}')
        .join('\n');

    final prompt = '''
너는 부산대학교 학생식당(금정회관) 메뉴 추천 챗봇 "밥묵자 AI"다.
아래 실시간 대기 현황을 근거로 학생의 질문에 답해라.

[실시간 대기 현황]
$context

[규칙]
- 한국어로 2~3문장, 친근한 반말 섞인 존댓말 톤 (예: "~어때요?", "~빨라요!")
- 반드시 위 현황의 대기 인원·예상 시간을 근거로 추천할 것
- 특정 라인을 추천하면 그 라인의 id를 lineId에 넣을 것 (추천 없으면 null)
- 아래 JSON 형식으로만 응답: {"answer": "...", "lineId": "..." 또는 null}

[학생 질문]
$question
''';

    final res = await http
        .post(
          Uri.parse('$_endpoint/$_model:generateContent?key=$_apiKey'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'contents': [
              {
                'parts': [
                  {'text': prompt}
                ]
              }
            ],
            'generationConfig': {
              'responseMimeType': 'application/json',
              'temperature': 0.7,
              // thinking 모델이라 사고 토큰이 출력 예산을 소진하면 JSON이 잘림
              // → 사고 비활성화 + 여유 있는 출력 한도
              'maxOutputTokens': 1024,
              'thinkingConfig': {'thinkingBudget': 0},
            },
          }),
        )
        .timeout(const Duration(seconds: 20));

    if (res.statusCode >= 400) {
      throw Exception('Gemini API 오류 (${res.statusCode}): '
          '${utf8.decode(res.bodyBytes)}');
    }

    final body = jsonDecode(utf8.decode(res.bodyBytes));
    final text = body['candidates']?[0]?['content']?['parts']?[0]?['text']
        as String?;
    if (text == null || text.isEmpty) {
      throw Exception('Gemini 응답이 비어 있습니다.');
    }

    return _parseRecommendation(text);
  }

  /// JSON 파싱 — 코드펜스 제거, 중괄호 범위 추출, 잘린 응답 복구까지 시도.
  /// 전부 실패하면 JSON 흔적을 걷어낸 순수 텍스트로 폴백 (원문 노출 방지).
  AiRecommendation _parseRecommendation(String raw) {
    var text = raw.trim();
    // ```json ... ``` 코드펜스 제거
    text = text
        .replaceAll(RegExp(r'^```(json)?', multiLine: true), '')
        .replaceAll('```', '')
        .trim();

    // 중괄호 범위만 추출해 파싱 시도
    final start = text.indexOf('{');
    final end = text.lastIndexOf('}');
    if (start != -1 && end > start) {
      try {
        final parsed =
            jsonDecode(text.substring(start, end + 1)) as Map<String, dynamic>;
        final lineId = parsed['lineId'] as String?;
        return AiRecommendation(
          answer: (parsed['answer'] as String?) ?? text,
          lineId: (lineId != null && lineId.isNotEmpty && lineId != 'null')
              ? lineId
              : null,
        );
      } catch (_) {/* 아래 복구 로직으로 */}
    }

    // 잘린 JSON 복구: "answer": "..." 값만 정규식으로 추출
    final answerMatch =
        RegExp(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)').firstMatch(text);
    if (answerMatch != null) {
      final answer = answerMatch.group(1)!.replaceAll(r'\"', '"');
      final lineMatch =
          RegExp(r'"lineId"\s*:\s*"([^"]+)"').firstMatch(text);
      return AiRecommendation(
        answer: answer,
        lineId: lineMatch?.group(1),
      );
    }

    // 최후 폴백: JSON 구조 문자를 걷어낸 텍스트
    return AiRecommendation(
      answer: text.replaceAll(RegExp(r'[{}"]'), '').trim(),
    );
  }
}
