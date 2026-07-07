import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// 하단 탭바 셸 — 탭 전환 시 각 탭의 네비게이션 상태 유지
class ScaffoldWithNavBar extends StatelessWidget {
  const ScaffoldWithNavBar({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
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
            NavigationDestination(
              icon: Icon(Icons.storefront_outlined),
              selectedIcon: Icon(Icons.storefront),
              label: '인근 상권',
            ),
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
