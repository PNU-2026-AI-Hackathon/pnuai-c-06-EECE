import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../core/formatters.dart';
import '../../data/models/meal_ticket.dart';

/// 이용 내역 — 사용 완료된 식권 히스토리 (최신순, 날짜 구분)
class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ticketsAsync = ref.watch(myTicketsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('이용 내역')),
      body: ticketsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('오류: $e')),
        data: (tickets) {
          final used = tickets
              .where((t) => t.status == TicketStatus.used)
              .toList()
            ..sort((a, b) => b.purchasedAt.compareTo(a.purchasedAt));

          if (used.isEmpty) return const _EmptyHistory();

          // 날짜별 그룹핑
          final items = <Widget>[];
          String? lastDate;
          for (final t in used) {
            final date =
                '${t.purchasedAt.month}월 ${t.purchasedAt.day}일';
            if (date != lastDate) {
              lastDate = date;
              items.add(Padding(
                padding: const EdgeInsets.fromLTRB(6, 16, 0, 8),
                child: Text(
                  date,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textWeak,
                  ),
                ),
              ));
            }
            items.add(_HistoryTile(ticket: t));
          }

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
            children: items,
          );
        },
      ),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({required this.ticket});

  final MealTicket ticket;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: kCardShadow,
      ),
      child: Material(
        color: Colors.transparent,
        child: ListTile(
        dense: true,
        leading: Container(
          width: 40,
          height: 40,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppColors.primary.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(
            Icons.restaurant,
            size: 20,
            color: AppColors.primary,
          ),
        ),
        title: Text(
          '${ticket.lineName} · ${ticket.menuName}',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            color: AppColors.textStrong,
          ),
        ),
        subtitle: Text(
          '${hhmm(ticket.purchasedAt)} · 대기번호 ${ticket.queueNumber}',
          style: const TextStyle(fontSize: 12, color: AppColors.textWeak),
        ),
        trailing: Text(
          won(ticket.price),
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w800,
            color: AppColors.textStrong,
          ),
        ),
        ),
      ),
    );
  }
}

class _EmptyHistory extends StatelessWidget {
  const _EmptyHistory();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.receipt_long_outlined,
              size: 48, color: AppColors.textWeak),
          SizedBox(height: 12),
          Text(
            '아직 이용 내역이 없어요',
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w800,
              color: AppColors.textStrong,
            ),
          ),
          SizedBox(height: 4),
          Text(
            '식권을 사용하면 여기에 기록돼요.',
            style: TextStyle(fontSize: 13, color: AppColors.textWeak),
          ),
        ],
      ),
    );
  }
}
