import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../features/ai/ai_screen.dart';
import '../features/home/home_screen.dart';
import '../features/profile/profile_screen.dart';
import '../features/restaurants/restaurants_screen.dart';
import '../features/shell/scaffold_with_nav_bar.dart';
import '../features/ticket/ticket_detail_screen.dart';
import '../features/ticket/tickets_screen.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();

final appRouter = GoRouter(
  navigatorKey: _rootNavigatorKey,
  initialLocation: '/home',
  routes: [
    // 하단 탭바 5개 (탭 전환 시 각 탭 상태 유지)
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
        StatefulShellBranch(routes: [
          GoRoute(
            path: '/restaurants',
            builder: (_, __) => const RestaurantsScreen(),
          ),
        ]),
        StatefulShellBranch(routes: [
          GoRoute(path: '/ai', builder: (_, __) => const AiScreen()),
        ]),
        StatefulShellBranch(routes: [
          GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
        ]),
      ],
    ),
    // QR 식권 상세 — 탭바를 덮는 전체 화면
    GoRoute(
      path: '/ticket/:id',
      parentNavigatorKey: _rootNavigatorKey,
      builder: (context, state) =>
          TicketDetailScreen(ticketId: state.pathParameters['id']!),
    ),
  ],
);
