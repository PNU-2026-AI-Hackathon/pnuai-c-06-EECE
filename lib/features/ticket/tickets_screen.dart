import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/formatters.dart';
import '../../data/models/meal_ticket.dart';

/// 내 식권 목록
class TicketsScreen extends ConsumerWidget {
  const TicketsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ticketsAsync = ref.watch(myTicketsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('내 식권')),
      body: ticketsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('오류: $e')),
        data: (tickets) {
          if (tickets.isEmpty) {
            return const Center(
              child: Text('구매한 식권이 없습니다.\n학식 탭에서 식권을 구매해 보세요!',
                  textAlign: TextAlign.center),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: tickets.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, i) => _TicketTile(ticket: tickets[i]),
          );
        },
      ),
    );
  }
}

class _TicketTile extends StatelessWidget {
  const _TicketTile({required this.ticket});

  final MealTicket ticket;

  Color _statusColor(BuildContext context) => switch (ticket.status) {
        TicketStatus.waiting => Colors.orange,
        TicketStatus.called => Colors.green,
        TicketStatus.used => Colors.grey,
      };

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(context);
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: const Icon(Icons.qr_code_2, size: 36),
        title: Text('${ticket.lineName} · ${ticket.menuName}'),
        subtitle: Text(
          '대기번호 ${ticket.queueNumber} · ${hhmm(ticket.purchasedAt)} 구매',
        ),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(999),
          ),
          child: Text(
            ticket.status.label,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.w700,
              fontSize: 12,
            ),
          ),
        ),
        onTap: () => context.push('/ticket/${ticket.id}'),
      ),
    );
  }
}
