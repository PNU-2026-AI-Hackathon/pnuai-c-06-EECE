import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../data/models/remote_waiting.dart';
import '../../data/models/restaurant.dart';

/// 제휴 식당 — 원격 웨이팅 + 할인
class RestaurantsScreen extends ConsumerWidget {
  const RestaurantsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final restaurantsAsync = ref.watch(restaurantsProvider);
    final waitingsAsync = ref.watch(myWaitingsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('부산대 제휴식당')),
      body: restaurantsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('오류: $e')),
        data: (restaurants) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // 내 웨이팅 현황
            ...waitingsAsync.maybeWhen(
              data: (waitings) => waitings
                  .map((w) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _MyWaitingCard(waiting: w),
                      ))
                  .toList(),
              orElse: () => const <Widget>[],
            ),
            for (final r in restaurants) ...[
              _RestaurantCard(restaurant: r),
              const SizedBox(height: 12),
            ],
          ],
        ),
      ),
    );
  }
}

class _MyWaitingCard extends StatelessWidget {
  const _MyWaitingCard({required this.waiting});

  final RemoteWaiting waiting;

  @override
  Widget build(BuildContext context) {
    final called = waiting.status == WaitingStatus.called;
    final color = called ? Colors.green : Colors.orange;
    return Card(
      color: color.withOpacity(0.08),
      child: ListTile(
        leading: Icon(
          called ? Icons.notifications_active : Icons.schedule,
          color: color,
        ),
        title: Text('${waiting.restaurantName} — 웨이팅 ${waiting.number}번'),
        subtitle: Text(
          called ? '입장 호출! 매장으로 이동해 주세요' : '내 앞 ${waiting.teamsAhead}팀',
          style: TextStyle(color: color, fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}

class _RestaurantCard extends ConsumerWidget {
  const _RestaurantCard({required this.restaurant});

  final Restaurant restaurant;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final r = restaurant;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Text(r.emoji, style: const TextStyle(fontSize: 34)),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    r.name,
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  Text(
                    '${r.category} · 도보 ${r.walkMinutes}분 · 대기 ${r.waitingTeams}팀',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '🎫 ${r.discountText}',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.primary,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            FilledButton.tonal(
              onPressed:
                  r.waitingAvailable ? () => _join(context, ref) : null,
              child: const Text('웨이팅'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _join(BuildContext context, WidgetRef ref) async {
    final waiting = await ref
        .read(restaurantRepositoryProvider)
        .joinWaiting(restaurant.id);
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          '${waiting.restaurantName} 웨이팅 ${waiting.number}번 등록! '
          '내 앞 ${waiting.teamsAhead}팀',
        ),
      ),
    );
  }
}
