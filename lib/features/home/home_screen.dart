import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/formatters.dart';
import '../../data/models/cafeteria_line.dart';

/// 홈 — 금정회관 라인별 실시간 대기 현황 + 식권 구매
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final linesAsync = ref.watch(cafeteriaLinesProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('금정회관 학생식당')),
      body: linesAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('오류: $e')),
        data: (lines) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
          children: [
            Row(
              children: [
                Icon(Icons.circle, size: 8, color: Colors.green.shade600),
                const SizedBox(width: 6),
                Text(
                  '실시간 · 앱 기준 대기 인원',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
            const SizedBox(height: 8),
            for (final line in lines) ...[
              _LineCard(line: line),
              const SizedBox(height: 12),
            ],
          ],
        ),
      ),
    );
  }
}

class _LineCard extends ConsumerWidget {
  const _LineCard({required this.line});

  final CafeteriaLine line;

  Color _congestionColor(CongestionLevel level) => switch (level) {
        CongestionLevel.relaxed => Colors.green,
        CongestionLevel.normal => Colors.orange,
        CongestionLevel.crowded => Colors.red,
      };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final color = _congestionColor(line.congestion);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  line.name,
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(width: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    line.congestion.label,
                    style: TextStyle(
                      color: color,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const Spacer(),
                Text(
                  line.location,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              line.todayMenu.join(' · '),
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                _Metric(label: '대기', value: '${line.waitingCount}명'),
                const SizedBox(width: 20),
                _Metric(label: '예상', value: '약 ${line.estimatedWaitMinutes}분'),
                const Spacer(),
                FilledButton(
                  onPressed: () => _purchase(context, ref),
                  child: Text('식권 구매 ${won(line.price)}'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _purchase(BuildContext context, WidgetRef ref) async {
    final confirmed = await showModalBottomSheet<bool>(
      context: context,
      builder: (sheetContext) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '${line.name} 식권 구매',
              style: Theme.of(sheetContext).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text('${line.todayMenu.first} · ${won(line.price)}'),
            const SizedBox(height: 4),
            Text(
              '구매 즉시 대기번호가 발급되고 배식 줄에 자동 등록됩니다.',
              style: Theme.of(sheetContext).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () => Navigator.pop(sheetContext, true),
              child: const Text('구매하기 (Mock 결제)'),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true || !context.mounted) return;

    final ticket =
        await ref.read(ticketRepositoryProvider).purchaseTicket(line.id);
    if (context.mounted) {
      context.push('/ticket/${ticket.id}');
    }
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.bodySmall),
        Text(
          value,
          style: Theme.of(context)
              .textTheme
              .titleMedium
              ?.copyWith(fontWeight: FontWeight.w800),
        ),
      ],
    );
  }
}
