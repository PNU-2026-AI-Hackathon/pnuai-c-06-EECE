import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../core/formatters.dart';
import '../../data/api/pnu_menu_service.dart';

/// 주간 식단 — 부산대 공식 식단안내 기준 (금정회관)
/// 1층 학생식당(정식/일품, 중식·석식) + 2층 교직원식당(정식, 중식)
class WeeklyMenuScreen extends ConsumerWidget {
  const WeeklyMenuScreen({super.key});

  static const _weekdays = ['월', '화', '수', '목', '금', '토', '일'];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final weekAsync = ref.watch(pnuMenuProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('주간 식단')),
      body: weekAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('오류: $e')),
        data: (week) {
          if (week.days.isEmpty) {
            return const Center(
              child: Text(
                '식단 데이터가 없습니다.',
                style: TextStyle(color: AppColors.textWeak),
              ),
            );
          }
          final days = [...week.days]..sort((a, b) => b.date.compareTo(a.date));
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
            children: [
              const Padding(
                padding: EdgeInsets.only(left: 4, bottom: 10),
                child: Text(
                  '출처: 부산대학교 공식 식단안내 · 네트워크 연결 시 자동 갱신',
                  style: TextStyle(fontSize: 11, color: AppColors.textWeak),
                ),
              ),
              for (final day in days) _DayCard(day: day),
            ],
          );
        },
      ),
    );
  }
}

class _DayCard extends StatelessWidget {
  const _DayCard({required this.day});

  final KumjungDayMenu day;

  bool get _isToday {
    final now = DateTime.now();
    return day.date.year == now.year &&
        day.date.month == now.month &&
        day.date.day == now.day;
  }

  @override
  Widget build(BuildContext context) {
    final weekday =
        WeeklyMenuScreen._weekdays[day.date.weekday - 1];

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(kRadiusCard),
        border: _isToday ? Border.all(color: AppColors.primary, width: 1.5) : null,
        boxShadow: kCardShadow,
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                '${day.date.month}/${day.date.day} ($weekday)',
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                  color: AppColors.textStrong,
                ),
              ),
              if (_isToday) ...[
                const SizedBox(width: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(kRadiusPill),
                  ),
                  child: const Text(
                    '오늘',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ],
          ),
          if (day.studentLunch.isNotEmpty)
            _MealGroup(
              title: '1층 학생식당 · 중식',
              sections: day.studentLunch,
            ),
          if (day.studentDinner.isNotEmpty)
            _MealGroup(
              title: '1층 학생식당 · 석식',
              sections: day.studentDinner,
            ),
          if (day.staffLunch.isNotEmpty)
            _MealGroup(
              title: '2층 교직원식당 · 중식 (외부인 이용가능)',
              sections: day.staffLunch,
            ),
          if (day.studentLunch.isEmpty &&
              day.studentDinner.isEmpty &&
              day.staffLunch.isEmpty)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text(
                '등록된 식단이 없습니다.',
                style: TextStyle(fontSize: 12, color: AppColors.textWeak),
              ),
            ),
        ],
      ),
    );
  }
}

class _MealGroup extends StatelessWidget {
  const _MealGroup({required this.title, required this.sections});

  final String title;
  final List<PnuMenuSection> sections;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 3,
                height: 12,
                margin: const EdgeInsets.only(right: 6),
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textWeak,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          for (final s in sections)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      '${s.name} ${won(s.price)}',
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        color: AppColors.primary,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      s.items.join(' · '),
                      style: const TextStyle(
                        fontSize: 13,
                        height: 1.5,
                        color: AppColors.textStrong,
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
