import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../app/providers.dart';
import '../../core/formatters.dart';
import '../../data/models/meal_ticket.dart';

/// QR 식권 상세 — 대기번호 + 호출 상태 실시간 갱신 (시연 핵심 화면)
class TicketDetailScreen extends ConsumerWidget {
  const TicketDetailScreen({super.key, required this.ticketId});

  final String ticketId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ticketAsync = ref.watch(ticketProvider(ticketId));

    return Scaffold(
      appBar: AppBar(title: const Text('모바일 식권')),
      body: ticketAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('오류: $e')),
        data: (ticket) => _TicketBody(ticket: ticket),
      ),
    );
  }
}

class _TicketBody extends ConsumerWidget {
  const _TicketBody({required this.ticket});

  final MealTicket ticket;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _StatusBanner(status: ticket.status),
          const SizedBox(height: 20),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  Text(
                    '${ticket.lineName} · ${ticket.menuName}',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 16),
                  QrImageView(
                    data: ticket.qrData,
                    version: QrVersions.auto,
                    size: 190,
                  ),
                  const SizedBox(height: 16),
                  Text('대기번호',
                      style: Theme.of(context).textTheme.bodySmall),
                  Text(
                    '${ticket.queueNumber}',
                    style: Theme.of(context)
                        .textTheme
                        .displayMedium
                        ?.copyWith(fontWeight: FontWeight.w800),
                  ),
                  if (ticket.status == TicketStatus.waiting)
                    Text('내 앞 대기 ${ticket.aheadCount}명'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            '${won(ticket.price)} · ${hhmm(ticket.purchasedAt)} 구매\n'
            '배식대에서 QR을 보여주시면 스캔과 동시에 체크인됩니다.',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 24),
          if (ticket.status != TicketStatus.used)
            OutlinedButton.icon(
              icon: const Icon(Icons.qr_code_scanner),
              label: const Text('(시연용) 배식대 QR 스캔 처리'),
              onPressed: () =>
                  ref.read(ticketRepositoryProvider).checkIn(ticket.id),
            ),
        ],
      ),
    );
  }
}

class _StatusBanner extends StatelessWidget {
  const _StatusBanner({required this.status});

  final TicketStatus status;

  @override
  Widget build(BuildContext context) {
    final (color, icon, text) = switch (status) {
      TicketStatus.waiting => (
          Colors.orange,
          Icons.hourglass_top,
          '대기 중입니다 — 호출되면 알려드릴게요',
        ),
      TicketStatus.called => (
          Colors.green,
          Icons.notifications_active,
          '호출되었습니다! 배식대로 이동해 주세요',
        ),
      TicketStatus.used => (
          Colors.grey,
          Icons.check_circle,
          '사용 완료된 식권입니다',
        ),
    };

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Icon(icon, color: color),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: TextStyle(color: color, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}
