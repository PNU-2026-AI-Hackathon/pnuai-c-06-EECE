import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../core/formatters.dart';
import '../../data/models/meal_ticket.dart';

/// 내 식권 목록 — 목업 톤 (티켓형 카드 + 상태 배지)
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
          if (tickets.isEmpty) return const _EmptyState();
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: tickets.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, i) => _TicketCard(ticket: tickets[i]),
          );
        },
      ),
    );
  }
}

/// 빈 상태 — 홈으로 유도하는 CTA
class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 72,
            height: 72,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(kRadiusPill),
            ),
            child: const Icon(
              Icons.confirmation_num_outlined,
              color: AppColors.primary,
              size: 34,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            '구매한 식권이 없어요',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w800,
              color: AppColors.textStrong,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            '홈에서 식권을 구매하면\n키오스크 줄 없이 바로 배식 줄에 서요!',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, color: AppColors.textWeak),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            icon: const Icon(Icons.home_outlined, size: 18),
            label: const Text('식권 구매하러 가기'),
            onPressed: () => context.go('/home'),
          ),
        ],
      ),
    );
  }
}

/// 티켓형 카드 — 좌측 상태 스트라이프 + 대기번호 강조
class _TicketCard extends StatelessWidget {
  const _TicketCard({required this.ticket});

  final MealTicket ticket;

  Color get _color => switch (ticket.status) {
        TicketStatus.waiting => AppColors.normal,
        TicketStatus.called => AppColors.accent,
        TicketStatus.used => AppColors.textWeak,
      };

  @override
  Widget build(BuildContext context) {
    final used = ticket.status == TicketStatus.used;

    return Opacity(
      opacity: used ? 0.55 : 1,
      child: GestureDetector(
        onTap: () => context.push('/ticket/${ticket.id}'),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(kRadiusCard),
            boxShadow: kCardShadow,
          ),
          child: IntrinsicHeight(
            child: Row(
              children: [
                // 좌측 상태 스트라이프 (티켓 절취선 느낌)
                Container(
                  width: 6,
                  decoration: BoxDecoration(
                    color: _color,
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(kRadiusCard),
                      bottomLeft: Radius.circular(kRadiusCard),
                    ),
                  ),
                ),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        // 대기번호 큰 숫자
                        Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Text(
                              '대기번호',
                              style: TextStyle(
                                fontSize: 10,
                                color: AppColors.textWeak,
                              ),
                            ),
                            Text(
                              // 호출/사용완료는 대기 순번이 없음 → '—'
                              ticket.queueNumber > 0
                                  ? '${ticket.queueNumber}'
                                  : '—',
                              style: const TextStyle(
                                fontSize: 26,
                                fontWeight: FontWeight.w900,
                                color: AppColors.primary,
                                height: 1.1,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(width: 14),
                        Container(
                          width: 1,
                          height: 48,
                          color: const Color(0xFFEDF0F5),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                ticket.lineName,
                                style: const TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w800,
                                  color: AppColors.textStrong,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                '${ticket.menuName} · ${hhmm(ticket.purchasedAt)} 구매',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.textWeak,
                                ),
                              ),
                              if (ticket.status == TicketStatus.waiting) ...[
                                const SizedBox(height: 4),
                                Text(
                                  '내 앞 대기 ${ticket.aheadCount}명',
                                  style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700,
                                    color: AppColors.normal,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 4,
                              ),
                              decoration: BoxDecoration(
                                color: _color.withValues(alpha: 0.12),
                                borderRadius:
                                    BorderRadius.circular(kRadiusPill),
                              ),
                              child: Text(
                                ticket.status.label,
                                style: TextStyle(
                                  color: _color,
                                  fontWeight: FontWeight.w800,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                            const SizedBox(height: 6),
                            const Icon(
                              Icons.qr_code_2,
                              size: 22,
                              color: AppColors.textWeak,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
