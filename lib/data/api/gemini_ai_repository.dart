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
      // 질문에 특정 음식/가게 키워드가 있으면 반경 내 키워드 검색을 추가
      // (예: "라멘집" — 위 45곳 목록에 없어도 카카오에서 직접 찾아줌)
      // null = 검색 불가(웹 프록시 미지원 등) → 섹션 생략, "없다" 단정 방지
      final keyword = _extractFoodKeyword(question);
      if (keyword != null) {
        var found = await _local.searchKeyword(keyword);
        var label = keyword;
        // 여러 단어 키워드가 0건이면 가장 긴 단어 하나로 재검색
        // (예: "코하루 어디있어" → 0건 → "코하루"로 재시도하면 잡힘)
        if (found != null && found.isEmpty && keyword.contains(' ')) {
          final longest = keyword
              .split(' ')
              .reduce((a, b) => a.length >= b.length ? a : b);
          final retry = await _local.searchKeyword(longest);
          if (retry != null && retry.isNotEmpty) {
            found = retry;
            label = longest;
          }
        }
        if (found != null) {
          nearbyContext += found.isNotEmpty
              ? '\n\n["$label" 검색 결과 — 부산대 반경 1.2km]\n'
                  '${found.map((p) => p.contextLine).join('\n')}'
              : '\n\n["$label" 키워드 검색은 0건 — 단, 위 목록에 있으면 그 정보는 유효함]';
        }
      }
    }

    // 역할·규칙은 systemInstruction으로 분리 (대화 턴과 섞이지 않게).
    // 주변 상권 데이터 유무에 따라 규칙을 바꿔 할루시네이션(지어내기)을 차단한다.
    final hasNearby = nearbyContext.isNotEmpty;
    final systemPrompt = '''
너는 부산대학교 점심 추천 챗봇 "밥묵자 AI"다.
사용자 메시지에 포함된 데이터만 근거로 답해라.
이전 대화 맥락을 기억하고 후속 질문("그럼 두 번째로 빠른 건?" 등)에 자연스럽게 이어서 답해라.

[사실 준수 — 최우선 규칙]
- 컨텍스트에 없는 식당 이름·메뉴·가격·대기 시간을 절대 만들어내지 마라.
- 모르는 것은 모른다고 말해라. 추측을 사실처럼 말하지 마라.
${hasNearby ? '''
[추천 우선순위]
1. 기본은 학생식당(금정회관) — 대기 인원·예상 시간을 근거로 추천
2. 학식 메뉴가 취향과 안 맞거나 모두 혼잡하거나 사용자가 다른 음식을 원하면,
   [부산대 주변 음식점] 목록에 있는 곳"만" 골라 이름·종류·도보 시간을 알려줘라
3. ["..." 검색 결과] 섹션이 있으면 그 목록을 최우선 근거로 써라
4. 키워드 검색이 0건이어도 [부산대 주변 음식점] 목록이나 이전 대화에서 언급한
   가게는 여전히 실존한다 — 방금 소개한 가게를 "없다"고 번복하지 마라.
   어느 목록에도 없을 때만 "찾지 못했다"고 말해라
5. 주변 음식점의 메뉴·가격·대기 시간은 데이터에 없다 — 솔직히 모른다고 하고,
   가게 이름·종류·도보 시간까지만 알려줘라''' : '''
[제한]
- 지금은 주변 음식점 데이터가 없다 — 학생식당(금정회관)만 추천해라.
- 학식 외 음식을 원하면 "지금은 학식 정보만 갖고 있어요"라고 솔직히 말하고,
  주변 식당 이름을 아는 척 지어내지 마라.'''}

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

    final body = jsonEncode({
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
    });

    // 무료 티어 특성상 일시 혼잡(503)·쿼터(429)가 흔함 → 1회 재시도 후
    // 그래도 실패하면 원문 JSON 대신 사람이 읽을 메시지로 던진다.
    http.Response res;
    for (var attempt = 1; ; attempt++) {
      res = await http
          .post(
            Uri.parse('$_endpoint/$_model:generateContent?key=$_apiKey'),
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(const Duration(seconds: 20));

      final retryable = res.statusCode == 503 || res.statusCode == 429;
      if (!retryable || attempt >= 2) break;
      await Future<void>.delayed(const Duration(seconds: 2));
    }

    if (res.statusCode == 503 || res.statusCode == 429) {
      throw Exception('지금 AI 사용량이 몰려 잠시 응답이 어려워요.\n'
          '몇 초 뒤 다시 시도해 주세요. (Gemini ${res.statusCode})');
    }
    if (res.statusCode >= 400) {
      throw Exception('AI 응답에 실패했어요. 잠시 후 다시 시도해 주세요. '
          '(Gemini ${res.statusCode})');
    }

    final resBody = jsonDecode(utf8.decode(res.bodyBytes));
    final text = resBody['candidates']?[0]?['content']?['parts']?[0]?['text']
        as String?;
    if (text == null || text.isEmpty) {
      throw Exception('Gemini 응답이 비어 있습니다.');
    }

    return _parseRecommendation(text);
  }

  /// 질문에서 음식/가게 키워드 추출 — 불용어를 걷어내고 남는 말을 검색어로.
  /// (예: "주변 라멘집 모두 알려줘" → "라멘집", "매운 게 땡겨" → null에 가까운 일반어)
  String? _extractFoodKeyword(String question) {
    const stop = {
      '주변', '주별', '근처', '부산대', '캠퍼스', '학교', '정문', '앞', '주위',
      '모두', '전부', '다', '좀', '그럼', '다른', '또', '더', '제일', '가장',
      '오늘', '지금', '점심', '저녁', '뭐', '뭔가', '어디', '먹을', '먹고',
      '싶어', '싶은데', '땡겨', '땡기는', '당겨', '먹을까', '갈까', '갈만한',
      '있어', '있나', '있나요', '있는', '알려줘', '알려줘요', '알려', '말해줘',
      '말해', '추천', '추천해줘', '추천해', '해줘', '해줘요', '해봐',
      '검색해봐', '검색해줘', '검색', '찾아줘', '찾아봐', '찾아', '맛집',
      '메뉴', '정보', '위치', '어디있어', '어디야', '어딨어', '가는법',
      '가격', '얼마', '얼마야', '얼마임',
      '거', '게', '것', '곳', '데',
    };
    final tokens = question
        .replaceAll(RegExp(r'[?!.,~]'), ' ')
        .split(RegExp(r'\s+'))
        .where((t) => t.isNotEmpty && !stop.contains(t))
        // 카카오는 "라멘집"보다 "라멘"이 상호 매칭이 잘 됨 → 접미사 '집' 제거
        .map((t) =>
            t.length >= 3 && t.endsWith('집') ? t.substring(0, t.length - 1) : t)
        .toList();
    if (tokens.isEmpty) return null;
    final keyword = tokens.join(' ');
    // 너무 짧거나(1글자) 문장 수준으로 길면 검색어로 부적합
    if (keyword.length < 2 || keyword.length > 12) return null;
    return keyword;
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
