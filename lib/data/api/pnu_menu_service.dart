import 'dart:convert';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter/services.dart' show rootBundle;
import 'package:html/parser.dart' as html_parser;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// 부산대 금정회관 식단 서비스 — 공식 "캠퍼스별 식단안내" 주간 테이블 파싱.
///
/// 확인된 공식 정보 (2026-07):
/// - 학생식당(PG002): 조식 08:00-11:00(방학 미운영) · 중식 11:00-17:00 · 석식 17:00-18:30
/// - 교직원식당: 중식 11:00-15:00
///
/// 데이터 3단 폴백: 네트워크(주간) → 캐시 → 내장 에셋 (웹 CORS/오프라인 대비)
class PnuMenuService {
  static const _base =
      'https://www.pusan.ac.kr/kor/CMS/MenuMgr/menuListOnBuilding.do?mCode=MN202';

  /// 금정회관 학생 식당 (공식 URL 파라미터로 확인됨)
  static const _studentUrl =
      '$_base&campus_gb=PUSAN&building_gb=R001&restaurant_code=PG002';

  /// 기본 페이지 = 금정회관 교직원 식당
  static const _staffUrl = _base;

  static const _cacheKey = 'pnu_menu_week_cache_v3';
  static const _assetPath = 'assets/data/kumjung_week_menu.json';

  /// 학생식당 운영시간 (시간대별 메뉴 전환 기준)
  static const lunchStartHour = 11; // 11:00
  static const dinnerStartHour = 17; // 17:00
  static const dinnerEndHour = 19; // 18:30 마감 → 19시부터는 다음날 안내 취급

  Future<KumjungWeekMenu> fetchWeek() async {
    var week = await _loadAsset();

    final cached = await _loadCache();
    if (cached != null) week = week.merge(cached);

    // 네트워크: 학생식당 주간(중식·석식) + 교직원식당 주간(중식)
    var network = const KumjungWeekMenu(days: []);
    try {
      final studentDays =
          _parseBuildingWeek(await _get(_studentUrl), staff: false);
      network = KumjungWeekMenu(days: studentDays);
      try {
        final staffDays =
            _parseBuildingWeek(await _get(_staffUrl), staff: true);
        network = network.merge(KumjungWeekMenu(days: staffDays));
      } catch (_) {/* 교직원 실패해도 학생 데이터는 사용 */}

      if (network.days.isNotEmpty) {
        debugPrint('[PnuMenu] 주간 식단 로드 성공: ${network.days.length}일');
        await _saveCache(network);
        week = week.merge(network);
      }
    } catch (e) {
      debugPrint('[PnuMenu] 네트워크 실패(웹 CORS/오프라인) → 내장 데이터 사용: $e');
    }
    return week;
  }

  Future<String> _get(String url) async {
    final res =
        await http.get(Uri.parse(url)).timeout(const Duration(seconds: 12));
    if (res.statusCode >= 400) throw Exception('HTTP ${res.statusCode}');
    return utf8.decode(res.bodyBytes);
  }

  // ── 주간 테이블 파싱 ──────────────────────────────────
  /// 열 = 날짜(월~토), 행 = 조식/중식/석식. [staff]면 중식만 staffLunch로.
  List<KumjungDayMenu> _parseBuildingWeek(String htmlText,
      {required bool staff}) {
    final doc = html_parser.parse(htmlText);
    final dateRe = RegExp(r'(\d{4})\.(\d{2})\.(\d{2})');

    Map<int, DateTime>? dates; // 셀 인덱스 → 날짜
    final byDate = <String, KumjungDayMenu>{};

    String key(DateTime d) =>
        '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

    for (final tr in doc.querySelectorAll('tr')) {
      final cells = tr.querySelectorAll('th,td');
      if (cells.isEmpty) continue;

      // 1) 헤더 행(날짜들) 탐지
      if (dates == null) {
        final found = <int, DateTime>{};
        for (var i = 0; i < cells.length; i++) {
          final m = dateRe.firstMatch(cells[i].text);
          if (m != null) {
            found[i] = DateTime(
              int.parse(m.group(1)!),
              int.parse(m.group(2)!),
              int.parse(m.group(3)!),
            );
          }
        }
        if (found.length >= 2) dates = found;
        continue;
      }

      // 2) 식사 행 (중식/석식)
      final label = cells.first.text;
      final isLunch = label.contains('중식');
      final isDinner = label.contains('석식');
      if (!isLunch && !isDinner) continue;
      if (staff && !isLunch) continue;

      for (final entry in dates.entries) {
        if (entry.key >= cells.length) continue;
        final sections = _parseSections(cells[entry.key].innerHtml);
        if (sections.isEmpty) continue;
        final k = key(entry.value);
        final prev = byDate[k] ??
            KumjungDayMenu(
              date: entry.value,
              studentLunch: const [],
              studentDinner: const [],
              staffLunch: const [],
            );
        byDate[k] = KumjungDayMenu(
          date: entry.value,
          studentLunch: staff
              ? prev.studentLunch
              : (isLunch ? sections : prev.studentLunch),
          studentDinner: staff
              ? prev.studentDinner
              : (isDinner ? sections : prev.studentDinner),
          staffLunch: staff ? sections : prev.staffLunch,
        );
      }
    }
    return byDate.values.toList()..sort((a, b) => a.date.compareTo(b.date));
  }

  List<PnuMenuSection> _parseSections(String cellHtml) {
    final lines = cellHtml
        .split(RegExp(r'<br\s*/?>', caseSensitive: false))
        .map((s) => s.replaceAll(RegExp(r'<[^>]+>'), '').trim())
        .where((s) => s.isNotEmpty)
        .toList();

    final sections = <PnuMenuSection>[];
    final header = RegExp(r'^(정식|일품|특정식)\s*-\s*([\d,]+)\s*원');
    String? name;
    int price = 0;
    var items = <String>[];

    void flush() {
      if (name != null && items.isNotEmpty) {
        sections.add(PnuMenuSection(name: name, price: price, items: items));
      }
      items = [];
    }

    for (final line in lines) {
      final m = header.firstMatch(line);
      if (m != null) {
        flush();
        name = m.group(1);
        price = int.parse(m.group(2)!.replaceAll(',', ''));
      } else if (name != null) {
        items.add(line);
      }
    }
    flush();
    return sections;
  }

  // ── 저장소 ────────────────────────────────────────────
  Future<KumjungWeekMenu> _loadAsset() async {
    try {
      final raw = await rootBundle.loadString(_assetPath);
      return KumjungWeekMenu.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (e) {
      debugPrint('[PnuMenu] 내장 에셋 로드 실패: $e');
      return const KumjungWeekMenu(days: []);
    }
  }

  Future<void> _saveCache(KumjungWeekMenu week) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_cacheKey, jsonEncode(week.toJson()));
  }

  Future<KumjungWeekMenu?> _loadCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(_cacheKey);
      if (raw == null) return null;
      return KumjungWeekMenu.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }
}

// ═══════════════════════════ 모델 ═══════════════════════════

class KumjungWeekMenu {
  final List<KumjungDayMenu> days;

  const KumjungWeekMenu({required this.days});

  /// 필드 단위 병합 — 같은 날짜는 [other]의 비어있지 않은 필드가 이김
  KumjungWeekMenu merge(KumjungWeekMenu other) {
    final map = {for (final d in days) _key(d.date): d};
    for (final d in other.days) {
      final prev = map[_key(d.date)];
      map[_key(d.date)] = prev == null
          ? d
          : KumjungDayMenu(
              date: d.date,
              studentLunch:
                  d.studentLunch.isNotEmpty ? d.studentLunch : prev.studentLunch,
              studentDinner: d.studentDinner.isNotEmpty
                  ? d.studentDinner
                  : prev.studentDinner,
              staffLunch:
                  d.staffLunch.isNotEmpty ? d.staffLunch : prev.staffLunch,
            );
    }
    final merged = map.values.toList()
      ..sort((a, b) => a.date.compareTo(b.date));
    return KumjungWeekMenu(days: merged);
  }

  static String _key(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  /// 오늘 데이터 (없으면 가장 가까운 과거)
  KumjungDayMenu? todayOrLatest({bool Function(KumjungDayMenu)? where}) {
    final now = DateTime.now();
    KumjungDayMenu? best;
    for (final d in days) {
      if (where != null && !where(d)) continue;
      if (d.date.isAfter(now)) continue;
      if (best == null || d.date.isAfter(best.date)) best = d;
    }
    return best;
  }

  Map<String, dynamic> toJson() =>
      {'days': [for (final d in days) d.toJson()]};

  factory KumjungWeekMenu.fromJson(Map<String, dynamic> json) => KumjungWeekMenu(
        days: [
          for (final d in (json['days'] as List))
            KumjungDayMenu.fromJson(d as Map<String, dynamic>)
        ],
      );
}

class KumjungDayMenu {
  final DateTime date;
  final List<PnuMenuSection> studentLunch;
  final List<PnuMenuSection> studentDinner;
  final List<PnuMenuSection> staffLunch;

  const KumjungDayMenu({
    required this.date,
    required this.studentLunch,
    required this.studentDinner,
    required this.staffLunch,
  });

  Map<String, dynamic> toJson() => {
        'date': date.toIso8601String(),
        'studentLunch': [for (final s in studentLunch) s.toJson()],
        'studentDinner': [for (final s in studentDinner) s.toJson()],
        'staffLunch': [for (final s in staffLunch) s.toJson()],
      };

  factory KumjungDayMenu.fromJson(Map<String, dynamic> json) {
    List<PnuMenuSection> parse(String key) => [
          for (final s in (json[key] as List? ?? []))
            PnuMenuSection.fromJson(s as Map<String, dynamic>)
        ];
    return KumjungDayMenu(
      date: DateTime.parse(json['date'] as String),
      studentLunch: parse('studentLunch'),
      studentDinner: parse('studentDinner'),
      staffLunch: parse('staffLunch'),
    );
  }
}

class PnuMenuSection {
  final String name;
  final int price;
  final List<String> items;

  const PnuMenuSection({
    required this.name,
    required this.price,
    required this.items,
  });

  Map<String, dynamic> toJson() =>
      {'name': name, 'price': price, 'items': items};

  factory PnuMenuSection.fromJson(Map<String, dynamic> json) => PnuMenuSection(
        name: json['name'] as String,
        price: json['price'] as int,
        items: [for (final i in (json['items'] as List)) i as String],
      );
}
