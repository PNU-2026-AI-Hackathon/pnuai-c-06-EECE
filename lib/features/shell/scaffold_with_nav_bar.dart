import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../data/models/meal_ticket.dart';

/// 하단 탭바 셸 — 탭 전환 시 각 탭의 네비게이션 상태 유지.
/// 어떤 탭에 있든 식권 호출(called) 전환을 감지해 알림 표시.
class ScaffoldWithNavBar extends ConsumerWidget {
  const ScaffoldWithNavBar({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // 호출 알림: waiting → called 전환 감지 (시연 핵심 순간)
    ref.listen(myTicketsProvider, (prev, next) {
      // 마이 탭 "호출 알림" 스위치가 꺼져 있으면 표시하지 않음
      if (!ref.read(callAlertEnabledProvider)) return;
      final prevTickets = prev?.valueOrNull ?? const <MealTicket>[];
      final nextTickets = next.valueOrNull ?? const <MealTicket>[];
      for (final t in nextTickets) {
        if (t.status != TicketStatus.called) continue;
        final wasCalled = prevTickets.any(
          (p) => p.id == t.id && p.status == TicketStatus.called,
        );
        if (wasCalled) continue;
        ScaffoldMessenger.of(context)
          ..clearSnackBars()
          ..showSnackBar(
            SnackBar(
              backgroundColor: AppColors.accent,
              behavior: SnackBarBehavior.floating,
              duration: const Duration(seconds: 6),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
              content: Text(
                '🔔 ${t.lineName} 호출! 대기번호 ${t.queueNumber}번, 배식대로 이동하세요',
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                ),
              ),
              action: SnackBarAction(
                label: 'QR 보기',
                textColor: Colors.white,
                onPressed: () => context.push('/ticket/${t.id}'),
              ),
            ),
          );
      }
    });

    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: Container(
        // 목업처럼 탭바가 콘텐츠 위에 살짝 떠 있는 느낌
        decoration: const BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Color(0x14204A8C),
              blurRadius: 16,
              offset: Offset(0, -4),
            ),
          ],
        ),
        child: NavigationBar(
          selectedIndex: navigationShell.currentIndex,
          onDestinationSelected: (index) => navigationShell.goBranch(
            index,
            initialLocation: index == navigationShell.currentIndex,
          ),
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home),
              label: '홈',
            ),
            NavigationDestination(
              icon: Icon(Icons.qr_code_2_outlined),
              selectedIcon: Icon(Icons.qr_code_2),
              label: '식권',
            ),
            // 인근 상권 탭은 MVP 범위에서 배제 (라우터 branch와 순서 일치 필수)
            NavigationDestination(
              icon: Icon(Icons.auto_awesome_outlined),
              selectedIcon: Icon(Icons.auto_awesome),
              label: 'AI 추천',
            ),
            NavigationDestination(
              icon: Icon(Icons.person_outline),
              selectedIcon: Icon(Icons.person),
              label: '마이',
            ),
          ],
        ),
      ),
    );
  }
}
