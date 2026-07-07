import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../core/formatters.dart';
import '../../data/models/meal_ticket.dart';

/// QR 식권 상세 — 목업(p.16) 스타일: 구매 완료 + 대형 QR + 오렌지 CTA
/// 대기번호 + 호출 상태 실시간 갱신 (시연 핵심 화면)
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
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _StatusHeader(status: ticket.status),
          const SizedBox(height: 16),
          // ── QR 카드 ──
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(kRadiusCard),
              boxShadow: kCardShadow,
            ),
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                QrImageView(
                  data: ticket.qrData,
                  version: QrVersions.auto,
                  size: 200,
                ),
                const SizedBox(height: 12),
                Text(
                  '${ticket.lineName} 1매 (${won(ticket.price)}) 구매 완료.\n'
                  '배식 라인 대기열에 자동 등록되었습니다.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 13,
                    height: 1.5,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textStrong,
                  ),
                ),
                const SizedBox(height: 16),
                const Divider(height: 1, color: Color(0xFFEDF0F5)),
                const SizedBox(height: 16),
                // ── 대기번호 (큰 숫자) ──
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    _BigMetric(label: '대기번호', value: '${ticket.queueNumber}'),
                    if (ticket.status == TicketStatus.waiting) ...[
                      Container(
                        width: 1,
                        height: 44,
                        color: const Color(0xFFEDF0F5),
                        margin: const EdgeInsets.symmetric(horizontal: 28),
                      ),
                      _BigMetric(label: '내 앞 대기', value: '${ticket.aheadCount}명'),
                    ],
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Text(
            '${ticket.menuName} · ${hhmm(ticket.purchasedAt)} 구매\n'
            '배식대에서 QR을 보여주시면 스캔과 동시에 체크인됩니다.',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12, color: AppColors.textWeak),
          ),
          const SizedBox(height: 16),
          // ── 오렌지 CTA 배너 (목업 하단) ──
          if (ticket.status == TicketStatus.waiting)
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              decoration: BoxDecoration(
                color: AppColors.accent,
                borderRadius: BorderRadius.circular(16),
                boxShadow: kCardShadow,
              ),
              child: const Text(
                '현장 키오스크 줄을 서지 말고\n바로 대기열로 합류하세요!',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  height: 1.4,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          const SizedBox(height: 16),
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

/// 상태 헤더 — "구매 완료!" / "호출됨!" / "사용 완료"
class _StatusHeader extends StatelessWidget {
  const _StatusHeader({required this.status});

  final TicketStatus status;

  @override
  Widget build(BuildContext context) {
    final (color, icon, title, sub) = switch (status) {
      TicketStatus.waiting => (
          AppColors.relaxed,
          Icons.check_circle,
          '구매 완료!',
          '호출되면 알려드릴게요',
        ),
      TicketStatus.called => (
          AppColors.accent,
          Icons.notifications_active,
          '호출되었습니다!',
          '지금 배식대로 이동해 주세요',
        ),
      TicketStatus.used => (
          AppColors.textWeak,
          Icons.task_alt,
          '사용 완료',
          '맛있게 드세요!',
        ),
    };

    return Column(
      children: [
        Icon(icon, color: color, size: 44),
        const SizedBox(height: 6),
        Text(
          title,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w900,
            color: color,
          ),
        ),
        Text(
          sub,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 13, color: AppColors.textWeak),
        ),
      ],
    );
  }
}

/// 큰 숫자 지표
class _BigMetric extends StatelessWidget {
  const _BigMetric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 12, color: AppColors.textWeak),
        ),
        Text(
          value,
          style: const TextStyle(
            fontSize: 34,
            fontWeight: FontWeight.w900,
            color: AppColors.primary,
            height: 1.2,
          ),
        ),
      ],
    );
  }
}
