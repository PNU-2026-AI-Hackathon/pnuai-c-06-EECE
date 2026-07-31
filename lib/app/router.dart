import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'providers.dart';
import '../features/ai/ai_screen.dart';
import '../features/auth/auth_controller.dart';
import '../features/auth/login_screen.dart';
import '../features/home/home_screen.dart';
import '../features/menu/weekly_menu_screen.dart';
import '../features/onboarding/onboarding_screen.dart';
import '../features/operator/operator_screen.dart';
import '../features/profile/history_screen.dart';
import '../features/profile/profile_screen.dart';
import '../features/shell/scaffold_with_nav_bar.dart';
import '../features/ticket/ticket_detail_screen.dart';
import '../features/ticket/tickets_screen.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();

/// go_router를 Riverpod provider로 노출 — 로그인 상태에 따라 리다이렉트.
final goRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/home',
    // 인증 상태가 바뀌면 리다이렉트 재평가
    refreshListenable: _AuthRefresh(ref),
    redirect: (context, state) {
      // 1) 온보딩 게이트 (첫 실행)
      final onboarded = ref.read(onboardingDoneProvider);
      final atOnboarding = state.matchedLocation == '/onboarding';
      if (!onboarded) return atOnboarding ? null : '/onboarding';
      if (atOnboarding) return '/home'; // 완료 후엔 로그인 게이트가 이어받음

      // 2) 로그인 게이트
      final loggedIn = ref.read(isLoggedInProvider);
      final atLogin = state.matchedLocation == '/login';
      if (!loggedIn) return atLogin ? null : '/login';
      if (atLogin) return '/home';
      return null;
    },
    routes: [
      GoRoute(
        path: '/onboarding',
        builder: (_, __) => const OnboardingScreen(),
      ),
      // 카카오 OAuth는 가입+로그인 통합 — 별도 회원가입 라우트 없음
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            ScaffoldWithNavBar(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/tickets', builder: (_, __) => const TicketsScreen()),
          ]),
          // 인근 상권(제휴식당)은 현재 MVP 범위에서 배제 — 복구 시 아래 주석 해제
          // StatefulShellBranch(routes: [
          //   GoRoute(
          //     path: '/restaurants',
          //     builder: (_, __) => const RestaurantsScreen(),
          //   ),
          // ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/ai', builder: (_, __) => const AiScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
          ]),
        ],
      ),
      GoRoute(
        path: '/ticket/:id',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) =>
            TicketDetailScreen(ticketId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/history',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (_, __) => const HistoryScreen(),
      ),
      GoRoute(
        path: '/operator',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (_, __) => const OperatorScreen(),
      ),
      GoRoute(
        path: '/menu',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (_, __) => const WeeklyMenuScreen(),
      ),
    ],
  );
});

/// 인증·온보딩 상태 변화를 Listenable로 변환 (go_router refresh용)
class _AuthRefresh extends ChangeNotifier {
  _AuthRefresh(Ref ref) {
    ref.listen(isLoggedInProvider, (_, __) => notifyListeners());
    ref.listen(onboardingDoneProvider, (_, __) => notifyListeners());
  }
}
