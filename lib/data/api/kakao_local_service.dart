import 'dart:convert';

import 'package:flutter/foundation.dart' show debugPrint, kIsWeb;
import 'package:http/http.dart' as http;

/// 카카오 로컬 API — 부산대 정문 반경 음식점 검색 (AI 추천 컨텍스트용).
///
/// - 모바일: dapi.kakao.com 직접 호출 (인증: `KakaoAK <REST API 키>`)
/// - 웹: 카카오 REST API가 브라우저 fetch를 CORS로 막음
///   → 백엔드 프록시 `GET {API_BASE_URL}/api/nearby[?q=키워드]` 경유
/// - 공개 지도 데이터 기반이라 식당 제휴·동의 불필요 (Phase B: 정보 추천)
/// - 캐시로 API 호출 최소화 (일 쿼터 보호)
///
/// ⚠️ 카카오는 페이지당 최대 15곳만 준다. 예전엔 "가까운 순 15곳"만 가져와서
///    정문 앞 60m 가게로만 채워졌음 → 지금은 3페이지(45곳) + 키워드 검색 병행.
class KakaoLocalService {
  KakaoLocalService(this._restApiKey);

  final String _restApiKey;

  static const _apiBaseUrl =
      String.fromEnvironment('API_BASE_URL', defaultValue: '');

  /// 검색 중심 좌표 — 부산대 정문 인근 (실측 검증됨: 강다짐/한솥 9~23m).
  static const _lng = '129.0843'; // x (경도)
  static const _lat = '35.2318'; // y (위도)

  /// 반경 — 캠퍼스~부산대역 상권까지 커버
  static const _radiusM = 1200;
  static const _pageSize = 15; // 카카오 페이지당 최대
  static const _pages = 3; // 15 × 3 = 45곳

  List<NearbyPlace>? _cache;
  DateTime? _cachedAt;
  final _keywordCache = <String, List<NearbyPlace>>{};

  bool get _unavailable =>
      (kIsWeb && _apiBaseUrl.isEmpty) || (!kIsWeb && _restApiKey.isEmpty);

  Map<String, String>? get _headers =>
      kIsWeb ? null : {'Authorization': 'KakaoAK $_restApiKey'};

  /// 반경 내 음식점 — 거리순 45곳 (3페이지 병합).
  /// 실패 시 이전 캐시 또는 빈 목록 (AI는 학식만으로 답함).
  Future<List<NearbyPlace>> nearbyRestaurants() async {
    if (_unavailable) return const [];

    final now = DateTime.now();
    if (_cache != null &&
        _cachedAt != null &&
        now.difference(_cachedAt!) < const Duration(minutes: 10)) {
      return _cache!;
    }

    try {
      final all = <NearbyPlace>[];
      for (var page = 1; page <= _pages; page++) {
        final uri = kIsWeb
            ? Uri.parse('$_apiBaseUrl/api/nearby?page=$page')
            : Uri.parse(
                'https://dapi.kakao.com/v2/local/search/category.json'
                '?category_group_code=FD6' // 음식점
                '&x=$_lng&y=$_lat&radius=$_radiusM'
                '&size=$_pageSize&page=$page&sort=distance',
              );
        final body = await _get(uri);
        all.addAll(_parseDocs(body));
        if (body['meta']?['is_end'] == true) break;
        // 웹 프록시가 page 파라미터를 아직 지원 안 하면 중복 방지 후 종료
        if (kIsWeb && page > 1 && all.length == _pageSize * (page - 1)) break;
      }
      final deduped = _dedupe(all);
      if (deduped.isNotEmpty) {
        _cache = deduped;
        _cachedAt = now;
      }
      debugPrint('[KakaoLocal] 주변 음식점 ${deduped.length}곳 로드 (반경 ${_radiusM}m)');
      return _cache ?? const [];
    } catch (e) {
      debugPrint('[KakaoLocal] 검색 실패 → 주변 상권 없이 진행: $e');
      return _cache ?? const [];
    }
  }

  /// 키워드 검색 — 질문에서 뽑은 음식/가게 키워드로 반경 내 검색.
  /// ("라멘집" 처럼 특정 종류를 물으면 45곳 목록에 없어도 찾아준다)
  Future<List<NearbyPlace>> searchKeyword(String keyword) async {
    if (_unavailable || keyword.trim().isEmpty) return const [];
    final key = keyword.trim();
    final cached = _keywordCache[key];
    if (cached != null) return cached;

    try {
      final uri = kIsWeb
          ? Uri.parse('$_apiBaseUrl/api/nearby?q=${Uri.encodeComponent(key)}')
          : Uri.parse(
              'https://dapi.kakao.com/v2/local/search/keyword.json'
              '?query=${Uri.encodeComponent(key)}'
              '&category_group_code=FD6'
              '&x=$_lng&y=$_lat&radius=$_radiusM'
              '&size=$_pageSize&sort=distance',
            );
      final result = _dedupe(_parseDocs(await _get(uri)));
      _keywordCache[key] = result;
      debugPrint('[KakaoLocal] 키워드 "$key" 검색: ${result.length}곳');
      return result;
    } catch (e) {
      debugPrint('[KakaoLocal] 키워드 "$key" 검색 실패: $e');
      return const [];
    }
  }

  // ── 내부 공통 ──────────────────────────────────────────
  Future<Map<String, dynamic>> _get(Uri uri) async {
    final res = await http
        .get(uri, headers: _headers)
        .timeout(const Duration(seconds: 8));
    if (res.statusCode >= 400) {
      throw Exception('HTTP ${res.statusCode}: ${res.body}');
    }
    return jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
  }

  List<NearbyPlace> _parseDocs(Map<String, dynamic> body) {
    final docs = (body['documents'] as List<dynamic>?) ?? const [];
    return [
      for (final d in docs) NearbyPlace.fromKakao(d as Map<String, dynamic>),
    ];
  }

  List<NearbyPlace> _dedupe(List<NearbyPlace> places) {
    final seen = <String>{};
    return [
      for (final p in places)
        if (p.name.isNotEmpty && seen.add(p.name)) p,
    ]..sort((a, b) => a.distanceM.compareTo(b.distanceM));
  }
}

/// 주변 음식점 1곳 (카카오 로컬 응답의 필요 필드만)
class NearbyPlace {
  const NearbyPlace({
    required this.name,
    required this.category,
    required this.distanceM,
    required this.walkMinutes,
    this.address = '',
    this.url = '',
  });

  factory NearbyPlace.fromKakao(Map<String, dynamic> d) {
    final distance = int.tryParse(d['distance']?.toString() ?? '') ?? 0;
    // "음식점 > 한식 > 국밥" → "한식/국밥"
    final cats = (d['category_name'] as String? ?? '')
        .split(' > ')
        .where((s) => s.isNotEmpty && s != '음식점')
        .toList();
    return NearbyPlace(
      name: d['place_name']?.toString() ?? '',
      category: cats.isEmpty ? '음식점' : cats.join('/'),
      distanceM: distance,
      // 도보 속도 약 67m/분
      walkMinutes: distance <= 0 ? 1 : (distance / 67).ceil().clamp(1, 30),
      address: d['road_address_name']?.toString() ?? '',
      url: d['place_url']?.toString() ?? '',
    );
  }

  final String name;
  final String category; // 예: 한식/국밥
  final int distanceM;
  final int walkMinutes;
  final String address;
  final String url;

  /// AI 프롬프트 컨텍스트 한 줄
  String get contextLine =>
      '- $name | $category | 도보 약 $walkMinutes분 (${distanceM}m)';
}
