import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart' show User;

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../core/env.dart';
import '../../data/models/meal_ticket.dart';
import '../auth/auth_controller.dart';

/// 마이 — 실서비스형 마이페이지
/// 구성: 프로필 카드 → 이용 현황 → 이용/지원/정보 그룹 메뉴 → 로그아웃(맨 아래)
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final tickets = ref.watch(myTicketsProvider).valueOrNull ?? const [];

    return Scaffold(
      appBar: AppBar(title: const Text('마이')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
        children: [
          _ProfileCard(user: user),
          const SizedBox(height: 12),
          _UsageSummary(tickets: tickets),
          const SizedBox(height: 20),
          const _SectionLabel('이용'),
          _MenuGroup(children: [
            _MenuTile(
              icon: Icons.qr_code_2_outlined,
              title: '내 식권 · 대기번호',
              onTap: () => context.go('/tickets'),
            ),
            _MenuTile(
              icon: Icons.receipt_long_outlined,
              title: '이용 내역',
              onTap: () => context.push('/history'),
            ),
            const _NotificationTile(),
          ]),
          const SizedBox(height: 16),
          const _SectionLabel('지원'),
          _MenuGroup(children: [
            _MenuTile(
              icon: Icons.campaign_outlined,
              title: '공지사항',
              onTap: () => _comingSoon(context),
            ),
            _MenuTile(
              icon: Icons.help_outline,
              title: '자주 묻는 질문',
              onTap: () => _comingSoon(context),
            ),
            _MenuTile(
              icon: Icons.chat_outlined,
              title: '문의하기',
              onTap: () => _comingSoon(context),
            ),
          ]),
          const SizedBox(height: 16),
          const _SectionLabel('정보'),
          _MenuGroup(children: [
            _MenuTile(
              icon: Icons.description_outlined,
              title: '이용약관 · 개인정보 처리방침',
              onTap: () => _comingSoon(context),
            ),
            const _MenuTile(
              icon: Icons.info_outline,
              title: '앱 버전',
              trailing: Text(
                '0.1.0 (MVP)',
                style: TextStyle(fontSize: 13, color: AppColors.textWeak),
              ),
            ),
            if (Env.useSupabase) const _DemoModeTile(),
            const _DemoResetTile(),
            _MenuTile(
              icon: Icons.storefront_outlined,
              title: '운영자 대시보드 (시연)',
              onTap: () => context.push('/operator'),
            ),
          ]),
          const SizedBox(height: 24),
          // ── 로그아웃/탈퇴 — 실서비스 관례상 맨 아래 배치 ──
          if (Env.useSupabase) ...[
            _LogoutButton(),
            const SizedBox(height: 4),
            Center(
              child: TextButton(
                onPressed: () => _comingSoon(context),
                child: const Text(
                  '회원 탈퇴',
                  style: TextStyle(fontSize: 12, color: Color(0xFFB4BCCA)),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  static void _comingSoon(BuildContext context) {
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(const SnackBar(content: Text('준비 중인 기능이에요.')));
  }
}

/// ── 프로필 카드: 카카오 아바타 + 닉네임 + 이메일 ──────────────
class _ProfileCard extends ConsumerWidget {
  const _ProfileCard({required this.user});

  final User? user; // Mock/마스터 모드에선 null

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final meta = user?.userMetadata ?? const <String, dynamic>{};
    final nickname =
        (meta['name'] ?? meta['nickname'] ?? meta['full_name'] ?? '부산대 학생')
            .toString();
    final avatarUrl = (meta['avatar_url'] ?? meta['picture'])?.toString();
    final email = user?.email;
    final isKakao = user != null;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(kRadiusCard),
        boxShadow: kCardShadow,
      ),
      padding: const EdgeInsets.all(18),
      child: Row(
        children: [
          // 아바타 (카카오 프로필 사진 → 없으면 기본 아이콘)
          CircleAvatar(
            radius: 28,
            backgroundColor: AppColors.primary.withValues(alpha: 0.10),
            backgroundImage:
                avatarUrl != null ? NetworkImage(avatarUrl) : null,
            child: avatarUrl == null
                ? const Icon(Icons.person, size: 30, color: AppColors.primary)
                : null,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        nickname,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w800,
                          color: AppColors.textStrong,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    // 로그인 방식 배지
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: isKakao
                            ? const Color(0xFFFEE500)
                            : AppColors.primary.withValues(alpha: 0.10),
                        borderRadius: BorderRadius.circular(kRadiusPill),
                      ),
                      child: Text(
                        isKakao ? '카카오' : 'Mock',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          color: isKakao
                              ? const Color(0xFF191919)
                              : AppColors.primary,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  email ?? (isKakao ? '이메일 미제공 계정' : '시연용 Mock 계정'),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textWeak,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// ── 이용 현황 요약 (내 식권 데이터 기반) ─────────────────────
class _UsageSummary extends StatelessWidget {
  const _UsageSummary({required this.tickets});

  final List<MealTicket> tickets;

  @override
  Widget build(BuildContext context) {
    final total = tickets.length;
    final used = tickets.where((t) => t.status == TicketStatus.used).length;
    // 키오스크 줄 스킵으로 절약한 시간 추정 (1회당 약 10분)
    final savedMinutes = used * 10;

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
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Row(
        children: [
          _Stat(label: '구매한 식권', value: '$total매'),
          _divider(),
          _Stat(label: '식사 완료', value: '$used회'),
          _divider(),
          _Stat(label: '아낀 대기시간', value: '$savedMinutes분'),
        ],
      ),
    );
  }

  Widget _divider() => Container(
        width: 1,
        height: 32,
        color: Colors.white.withValues(alpha: 0.25),
      );
}

class _Stat extends StatelessWidget {
  const _Stat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        children: [
          Text(
            value,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w900,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: const TextStyle(fontSize: 11, color: Colors.white70),
          ),
        ],
      ),
    );
  }
}

/// ── 섹션 라벨/그룹/타일 ─────────────────────────────────────
class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 6, bottom: 8),
      child: Text(
        text,
        style: const TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w800,
          color: AppColors.textWeak,
        ),
      ),
    );
  }
}

class _MenuGroup extends StatelessWidget {
  const _MenuGroup({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(kRadiusCard),
        boxShadow: kCardShadow,
      ),
      child: Column(
        children: [
          for (final (i, child) in children.indexed) ...[
            if (i > 0)
              const Divider(
                height: 1,
                indent: 52,
                color: Color(0xFFF0F2F7),
              ),
            child,
          ],
        ],
      ),
    );
  }
}

class _MenuTile extends StatelessWidget {
  const _MenuTile({
    required this.icon,
    required this.title,
    this.onTap,
    this.trailing,
  });

  final IconData icon;
  final String title;
  final VoidCallback? onTap;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      dense: true,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
      leading: Icon(icon, size: 22, color: AppColors.textStrong),
      title: Text(
        title,
        style: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: AppColors.textStrong,
        ),
      ),
      trailing: trailing ??
          const Icon(Icons.chevron_right, size: 20, color: Color(0xFFB4BCCA)),
      onTap: onTap,
    );
  }
}

/// ── 알림 설정 — callAlertEnabledProvider와 연동 (실제 호출 스낵바 제어)
class _NotificationTile extends ConsumerWidget {
  const _NotificationTile();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final enabled = ref.watch(callAlertEnabledProvider);
    return _MenuTile(
      icon: Icons.notifications_outlined,
      title: '호출 알림',
      trailing: Switch(
        value: enabled,
        activeThumbColor: AppColors.primary,
        onChanged: (v) async {
          ref.read(callAlertEnabledProvider.notifier).state = v;
          final prefs = await SharedPreferences.getInstance();
          await prefs.setBool('notify_enabled', v);
        },
      ),
    );
  }
}

/// ── 시연(Mock) 모드 스위치 ──────────────────────────────────
/// 켜면 전체 데이터가 Mock으로 전환 (시연 중 서버 장애 폴백용).
/// 끄면 실서버로 복귀 — 로그인 세션이 없으면 로그인 화면으로 이동됨.
class _DemoModeTile extends ConsumerWidget {
  const _DemoModeTile();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final demo = ref.watch(demoModeProvider);
    return _MenuTile(
      icon: Icons.science_outlined,
      title: '시연 모드 (Mock 데이터)',
      trailing: Switch(
        value: demo,
        activeThumbColor: AppColors.accent,
        onChanged: (v) {
          ref.read(demoModeProvider.notifier).state = v;
          ScaffoldMessenger.of(context)
            ..clearSnackBars()
            ..showSnackBar(
              SnackBar(
                content: Text(
                  v ? '시연 모드 ON — Mock 데이터로 동작합니다.' : '시연 모드 OFF — 실서버로 복귀합니다.',
                ),
              ),
            );
        },
      ),
    );
  }
}

/// ── 데모 데이터 초기화 (Mock 사용 중일 때만 노출) ─────────────
/// 시연 리허설을 처음 상태(식권 없음, 초기 대기 인원)로 되돌린다.
class _DemoResetTile extends ConsumerWidget {
  const _DemoResetTile();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usingMock = !ref.watch(useSupabaseProvider);
    if (!usingMock) return const SizedBox.shrink();

    return _MenuTile(
      icon: Icons.restart_alt,
      title: '데모 데이터 초기화',
      onTap: () {
        // Mock 데이터소스를 재생성 → 모든 화면이 초기 상태로
        ref.invalidate(campusDataSourceProvider);
        ScaffoldMessenger.of(context)
          ..clearSnackBars()
          ..showSnackBar(
            const SnackBar(content: Text('데모 데이터를 초기 상태로 되돌렸어요.')),
          );
      },
    );
  }
}

/// ── 로그아웃 (확인 다이얼로그 → 로그인 화면 복귀) ─────────────
class _LogoutButton extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return OutlinedButton(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.crowded,
        side: BorderSide(color: AppColors.crowded.withValues(alpha: 0.4)),
      ),
      onPressed: () async {
        final confirmed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20),
            ),
            title: const Text('로그아웃'),
            content: const Text('정말 로그아웃하시겠어요?'),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('취소'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(dialogContext, true),
                child: const Text('로그아웃'),
              ),
            ],
          ),
        );
        if (confirmed != true) return;

        // 마스터 세션 해제 + Supabase 로그아웃 → 라우터가 /login으로 보냄
        ref.read(devSessionProvider.notifier).state = false;
        try {
          await ref.read(authControllerProvider).signOut();
        } catch (_) {
          // 마스터 로그인 등 세션이 없는 경우 무시
        }
      },
      child: const Text(
        '로그아웃',
        style: TextStyle(fontWeight: FontWeight.w700),
      ),
    );
  }
}
