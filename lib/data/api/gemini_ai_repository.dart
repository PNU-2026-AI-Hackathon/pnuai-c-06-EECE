import 'dart:convert';

import 'package:flutter/foundation.dart' show debugPrint, kDebugMode;
import 'package:http/http.dart' as http;

import '../../core/formatters.dart';
import '../models/cafeteria_line.dart';
import '../repositories/ai_repository.dart';
import 'kakao_local_service.dart';

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
  GeminiAiRepository(this._apiKey, {KakaoLocalService? local}) : _local = local;

  final String _apiKey;

  /// 주변 상권 검색 (없으면 학식만으로 추천 — Phase B 선택 기능)
  final KakaoLocalService? _local;

  static const _model = 'gemini-2.5-flash';
  static const _endpoint =
      'https://generativelanguage.googleapis.com/v1beta/models';

  @override
  Future<AiRecommendation> ask(
    String question, {
    List<CafeteriaLine> lines = const [],
    List<AiChatTurn> history = const [],
  }) async {
    final context = lines
        .map((l) => '- id:"${l.id}" | ${l.name} | 대기 ${l.waitingCount}명 '
            '(약 ${l.estimatedWaitMinutes}분, ${l.congestion.label}) | '
            '${won(l.price)} | 오늘 메뉴: ${l.todayMenu.join(', ')}')
        .join('\n');

    // 주변 상권 (카카오 로컬 API) — 실패해도 학식만으로 추천 가능
    var nearbyContext = '';
    if (_local != null) {
      final places = await _local.nearbyRestaurants();
      if (places.isNotEmpty) {
        nearbyContext = '\n\n[부산대 주변 음식점 — 거리순, 대기 정보 없음]\n'
            '${places.map((p) => p.contextLine).join('\n')}';
      }
    }

    // 역할·규칙은 systemInstruction으로 분리 (대화 턴과 섞이지 않게)
    const systemPrompt = '''
너는 부산대학교 점심 추천 챗봇 "밥묵자 AI"다.
사용자 메시지에 포함된 실시간 대기 현황과 주변 음식점 목록을 근거로 답해라.
이전 대화 맥락을 기억하고 후속 질문("그럼 두 번째로 빠른 건?" 등)에 자연스럽게 이어서 답해라.

[추천 우선순위]
1. 기본은 학생식당(금정회관) — 대기 인원·예상 시간을 근거로 추천
2. 학식 메뉴가 사용자 취향과 안 맞거나, 학식이 모두 혼잡하거나, 사용자가 다른 음식을
   원하면 [부산대 주변 음식점]에서 골라 이름·종류·도보 시간을 알려줘라
3. 주변 음식점은 실시간 대기 정보가 없다 — 대기 시간을 지어내지 말 것

[규칙]
- 한국어로 2~3문장, 친근한 반말 섞인 존댓말 톤 (예: "~어때요?", "~빨라요!")
- 학식 추천 근거는 반드시 현황의 대기 인원·예상 시간일 것
- 특정 학식 라인을 추천하면 그 라인의 id를 lineId에 넣을 것
  (주변 음식점 추천이거나 추천 없으면 null)
- 아래 JSON 형식으로만 응답: {"answer": "...", "lineId": "..." 또는 null}
''';

    // 이전 대화 턴 (최근 10턴만 — 토큰 절약)
    final turns = <Map<String, dynamic>>[
      for (final t in history.length > 10
          ? history.sublist(history.length - 10)
          : history)
        {
          'role': t.isUser ? 'user' : 'model',
          'parts': [
            {'text': t.text}
          ],
        },
      // 현재 질문 — 최신 대기 현황을 함께 전달 (턴마다 갱신된 데이터 사용)
      {
        'role': 'user',
        'parts': [
          {
            'text': '[실시간 대기 현황]\n$context$nearbyContext\n\n[질문]\n$question',
          }
        ],
      },
    ];

    // 컨텍스트 튜닝용 — 디버그 빌드에서 AI에게 전달되는 원문 확인
    if (kDebugMode) {
      debugPrint('───[GeminiAI 컨텍스트]───\n'
          '[실시간 대기 현황]\n$context$nearbyContext\n──────────────');
    }

    final res = await http
        .post(
          Uri.parse('$_endpoint/$_model:generateContent?key=$_apiKey'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'systemInstruction': {
              'parts': [
                {'text': systemPrompt}
              ]
            },
            'contents': turns,
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
