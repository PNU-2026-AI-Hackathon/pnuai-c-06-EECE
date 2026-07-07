import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../core/formatters.dart';
import '../../data/models/cafeteria_line.dart';
import '../../data/models/meal_ticket.dart';

/// 홈 — 수정계획서 목업(p.14) 스타일
/// 그라데이션 헤더 + AI 검색바 + 라인별 대기 카드 + 식권 구매 카드 + AI 추천 배너
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final linesAsync = ref.watch(cafeteriaLinesProvider);
    final tickets = ref.watch(myTicketsProvider).valueOrNull ?? const [];

    return Scaffold(
      body: linesAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('오류: $e')),
        data: (lines) => ListView(
          padding: EdgeInsets.zero,
          children: [
            const _GradientHeader(),
            const SizedBox(height: 20),
            const _SectionHeader(),
            const SizedBox(height: 10),
            for (final line in lines)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                child: _LineCard(
                  line: line,
                  myTicket: _activeTicketFor(tickets, line.id),
                ),
              ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: _TicketPurchaseCard(lines: lines),
            ),
            const SizedBox(height: 12),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: _AiBanner(lines: lines),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  MealTicket? _activeTicketFor(List<MealTicket> tickets, String lineId) {
    for (final t in tickets) {
      if (t.lineId == lineId && t.status != TicketStatus.used) return t;
    }
    return null;
  }
}

/// ── 그라데이션 헤더 (로고 + 타이틀 + AI 검색바) ─────────────
class _GradientHeader extends StatelessWidget {
  const _GradientHeader();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [AppColors.gradientTop, AppColors.gradientBottom],
        ),
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(28)),
      ),
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      child: SafeArea(
        bottom: false,
        child: Column(
          children: [
            const SizedBox(height: 12),
            Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(kRadiusPill),
                  ),
                  child: const Text(
                    '밥',
                    style: TextStyle(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w900,
                      fontSize: 18,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'PNU 밥묵자',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      Text(
                        '부산대 학식 · 인근 상권 통합 웨이팅',
                        style: TextStyle(color: Colors.white70, fontSize: 12),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => context.go('/profile'),
                  icon: const Icon(Icons.person_outline, color: Colors.white),
                ),
              ],
            ),
            const SizedBox(height: 14),
            // AI 자연어 검색바 → AI 추천 탭으로 이동
            GestureDetector(
              onTap: () => context.go('/ai'),
              child: Container(
                height: 44,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(kRadiusPill),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.search, color: AppColors.textWeak, size: 20),
                    SizedBox(width: 8),
                    Text(
                      '"오늘 매콤한 거 땡기는 거"',
                      style: TextStyle(color: AppColors.textWeak, fontSize: 14),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// ── 섹션 헤더 ───────────────────────────────────────────
class _SectionHeader extends StatelessWidget {
  const _SectionHeader();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          const Text(
            '학생식당',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w900,
              color: AppColors.textStrong,
            ),
          ),
          const SizedBox(width: 8),
          const Expanded(
            child: Text(
              '금정회관 · 실시간 대기 현황',
              style: TextStyle(fontSize: 12, color: AppColors.textWeak),
            ),
          ),
          Row(
            children: [
              Icon(Icons.circle, size: 8, color: Colors.green.shade600),
              const SizedBox(width: 4),
              const Text(
                '실시간',
                style: TextStyle(fontSize: 12, color: AppColors.textWeak),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// ── 라인별 대기 카드 (프로그레스 바 + 상태 텍스트) ──────────
class _LineCard extends StatelessWidget {
  const _LineCard({required this.line, this.myTicket});

  final CafeteriaLine line;
  final MealTicket? myTicket;

  Color get _color => switch (line.congestion) {
        CongestionLevel.relaxed => AppColors.relaxed,
        CongestionLevel.normal => AppColors.normal,
        CongestionLevel.crowded => AppColors.crowded,
      };

  @override
  Widget build(BuildContext context) {
    // 30명 기준으로 바 채움 (혼잡 임계선 이상이면 가득)
    final fraction = (line.waitingCount / 30).clamp(0.06, 1.0);

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(kRadiusCard),
        boxShadow: kCardShadow,
      ),
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                line.name,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textStrong,
                ),
              ),
              const SizedBox(width: 8),
              if (myTicket != null) _MyTurnBadge(ticket: myTicket!),
              const Spacer(),
              Text(
                '${line.congestion.label} · 약 ${line.estimatedWaitMinutes}분',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  color: _color,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(kRadiusPill),
            child: LinearProgressIndicator(
              value: fraction.toDouble(),
              minHeight: 8,
              backgroundColor: const Color(0xFFEDF0F5),
              valueColor: AlwaysStoppedAnimation(_color),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Text(
                '대기 ${line.waitingCount}명',
                style: const TextStyle(
                  fontSize: 12,
                  color: AppColors.textWeak,
                ),
              ),
              const Spacer(),
              Expanded(
                flex: 3,
                child: Text(
                  '메뉴: ${line.todayMenu.join(' · ')}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.right,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textWeak,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// "내 차례 · N번째" 오렌지 배지
class _MyTurnBadge extends StatelessWidget {
  const _MyTurnBadge({required this.ticket});

  final MealTicket ticket;

  @override
  Widget build(BuildContext context) {
    final text = ticket.status == TicketStatus.called
        ? '호출됨!'
        : '내 차례 · ${ticket.aheadCount + 1}번째';
    return GestureDetector(
      onTap: () => context.push('/ticket/${ticket.id}'),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: AppColors.accent,
          borderRadius: BorderRadius.circular(kRadiusPill),
        ),
        child: Text(
          text,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 11,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

/// ── "식권 구매하기" 블루 대형 카드 ──────────────────────────
class _TicketPurchaseCard extends ConsumerWidget {
  const _TicketPurchaseCard({required this.lines});

  final List<CafeteriaLine> lines;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.gradientTop, AppColors.gradientBottom],
        ),
        borderRadius: BorderRadius.circular(kRadiusCard),
        boxShadow: kCardShadow,
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(
                  Icons.confirmation_num_outlined,
                  color: Colors.white,
                  size: 20,
                ),
              ),
              const SizedBox(width: 10),
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '식권 구매하기',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  Text(
                    '원하는 식권을 선택해 구매하세요',
                    style: TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              for (final (i, line) in lines.indexed) ...[
                if (i > 0) const SizedBox(width: 10),
                Expanded(child: _TicketOption(line: line)),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

/// 티켓 옵션 (흰색 미니 카드) — 탭하면 구매 시트
class _TicketOption extends ConsumerWidget {
  const _TicketOption({required this.line});

  final CafeteriaLine line;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return GestureDetector(
      onTap: () => showPurchaseSheet(context, ref, line),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
        child: Column(
          children: [
            const Icon(
              Icons.ramen_dining_outlined,
              color: AppColors.primary,
              size: 26,
            ),
            const SizedBox(height: 6),
            Text(
              line.name,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w800,
                color: AppColors.textStrong,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              won(line.price),
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w900,
                color: AppColors.primary,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              line.todayMenu.take(4).join('\n'),
              textAlign: TextAlign.center,
              maxLines: 4,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 10,
                height: 1.5,
                color: AppColors.textWeak,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// ── AI 추천 배너 ────────────────────────────────────────
class _AiBanner extends StatelessWidget {
  const _AiBanner({required this.lines});

  final List<CafeteriaLine> lines;

  @override
  Widget build(BuildContext context) {
    if (lines.isEmpty) return const SizedBox.shrink();
    final fastest = lines.reduce(
      (a, b) => a.estimatedWaitMinutes <= b.estimatedWaitMinutes ? a : b,
    );

    return GestureDetector(
      onTap: () => context.go('/ai'),
      child: Container(
        height: 48,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: BoxDecoration(
          color: AppColors.primary,
          borderRadius: BorderRadius.circular(kRadiusPill),
          boxShadow: kCardShadow,
        ),
        child: Row(
          children: [
            Container(
              width: 26,
              height: 26,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(kRadiusPill),
              ),
              child: const Text(
                'AI',
                style: TextStyle(
                  color: AppColors.primary,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'AI 추천 · 지금은 ${fastest.name}이 가장 빨라요 (약 ${fastest.estimatedWaitMinutes}분)',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            const Icon(Icons.chevron_right, color: Colors.white70, size: 20),
          ],
        ),
      ),
    );
  }
}

/// ── 식권 구매 시트 (기존 흐름 유지: 확인 → 구매 → 상세로 이동) ──
Future<void> showPurchaseSheet(
  BuildContext context,
  WidgetRef ref,
  CafeteriaLine line,
) async {
  final confirmed = await showModalBottomSheet<bool>(
    context: context,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    builder: (sheetContext) => Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            '${line.name} 식권 구매',
            style: const TextStyle(
              fontSize: 19,
              fontWeight: FontWeight.w900,
              color: AppColors.textStrong,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '${line.todayMenu.first} · ${won(line.price)}',
            style: const TextStyle(fontSize: 14, color: AppColors.textStrong),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.accentSoft,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Row(
              children: [
                Icon(Icons.bolt, color: AppColors.accent, size: 18),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '구매 즉시 대기번호 발급! 키오스크 줄 없이 바로 배식 줄로 가세요.',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: AppColors.accent,
                    ),
                  ),
                ),
              ],
            ),
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

  try {
    final ticket =
        await ref.read(ticketRepositoryProvider).purchaseTicket(line.id);
    if (context.mounted) {
      context.push('/ticket/${ticket.id}');
    }
  } catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }
}
