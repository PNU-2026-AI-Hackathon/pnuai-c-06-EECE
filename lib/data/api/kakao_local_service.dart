import 'dart:convert';

import 'package:flutter/foundation.dart' show debugPrint, kIsWeb;
import 'package:http/http.dart' as http;

/// 카카오 로컬 API — 부산대 정문 반경 음식점 검색 (AI 추천 컨텍스트용).
///
/// - 인증: `KakaoAK <REST API 키>` (카카오 로그인과 동일한 키)
/// - 공개 지도 데이터 기반이라 식당 제휴·동의 불필요 (Phase B: 정보 추천)
/// - 웹(브라우저)은 카카오 REST API의 CORS 제한으로 미지원 → 빈 목록 반환
///   (모바일 앱은 무관 — 시연은 실기기 기준)
/// - 10분 캐시로 API 호출 최소화 (일 쿼터 보호)
class KakaoLocalService {
  KakaoLocalService(this._restApiKey);

  final String _restApiKey;

  /// 검색 중심 좌표 — 부산대 정문 인근.
  /// 상권 범위를 조정하고 싶으면 이 좌표/반경만 바꾸면 됨.
  static const _lng = '129.0843'; // x (경도)
  static const _lat = '35.2318'; // y (위도)
  static const _radiusM = 800;
  static const _size = 15; // 카카오 최대 15

  List<NearbyPlace>? _cache;
  DateTime? _cachedAt;

  /// 반경 내 음식점 — 거리순. 실패 시 이전 캐시 또는 빈 목록 (AI는 학식만으로 답함).
  Future<List<NearbyPlace>> nearbyRestaurants() async {
    if (kIsWeb || _restApiKey.isEmpty) return const [];

    final now = DateTime.now();
    if (_cache != null &&
        _cachedAt != null &&
        now.difference(_cachedAt!) < const Duration(minutes: 10)) {
      return _cache!;
    }

    try {
      final uri = Uri.parse(
        'https://dapi.kakao.com/v2/local/search/category.json'
        '?category_group_code=FD6' // 음식점
        '&x=$_lng&y=$_lat&radius=$_radiusM&size=$_size&sort=distance',
      );
      final res = await http.get(
        uri,
        headers: {'Authorization': 'KakaoAK $_restApiKey'},
      ).timeout(const Duration(seconds: 8));

      if (res.statusCode >= 400) {
        throw Exception('HTTP ${res.statusCode}: ${res.body}');
      }

      final docs = (jsonDecode(utf8.decode(res.bodyBytes))['documents']
              as List<dynamic>?) ??
          const [];
      _cache = [
        for (final d in docs) NearbyPlace.fromKakao(d as Map<String, dynamic>),
      ];
      _cachedAt = now;
      debugPrint('[KakaoLocal] 부산대 주변 음식점 ${_cache!.length}곳 로드');
      return _cache!;
    } catch (e) {
      debugPrint('[KakaoLocal] 검색 실패 → 주변 상권 없이 진행: $e');
      return _cache ?? const [];
    }
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
