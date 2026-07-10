import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';

/// 첫 실행 온보딩 — 서비스 핵심 3가지를 3장으로 소개.
/// 완료 시 onboardingDoneProvider가 true가 되고 라우터가 로그인/홈으로 보냄.
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _controller = PageController();
  int _page = 0;

  static const _pages = [
    (
      icon: Icons.groups_outlined,
      title: '줄 서기 전에,\n대기 현황부터 확인하세요',
      desc: '금정회관 라인별 대기 인원과 예상 시간을\n실시간으로 보여드려요.',
    ),
    (
      icon: Icons.qr_code_2,
      title: '키오스크 줄은 이제 그만,\n모바일 QR 식권',
      desc: '앱에서 구매하면 대기번호가 바로 발급되고\nQR 하나로 배식대를 통과해요.',
    ),
    (
      icon: Icons.notifications_active_outlined,
      title: '내 차례가 오면\n자동으로 알려드려요',
      desc: '자리가 나면 앱이 먼저 알아채고 호출해요.\n줄 대신 폰만 보고 기다리세요.',
    ),
  ];

  bool get _isLast => _page == _pages.length - 1;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _finish() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarding_done', true);
    ref.read(onboardingDoneProvider.notifier).state = true;
    // 라우터 redirect가 로그인/홈으로 자동 이동시킴
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          children: [
            // 건너뛰기
            Align(
              alignment: Alignment.centerRight,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(0, 8, 12, 0),
                child: TextButton(
                  onPressed: _finish,
                  child: const Text(
                    '건너뛰기',
                    style: TextStyle(fontSize: 13, color: AppColors.textWeak),
                  ),
                ),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: _pages.length,
                onPageChanged: (i) => setState(() => _page = i),
                itemBuilder: (_, i) => _OnboardPage(
                  icon: _pages[i].icon,
                  title: _pages[i].title,
                  desc: _pages[i].desc,
                ),
              ),
            ),
            // 페이지 인디케이터
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                for (var i = 0; i < _pages.length; i++)
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 250),
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    width: _page == i ? 22 : 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _page == i
                          ? AppColors.primary
                          : const Color(0xFFDDE4EE),
                      borderRadius: BorderRadius.circular(kRadiusPill),
                    ),
                  ),
              ],
            ),
            // 다음 / 시작하기
            Padding(
              padding: const EdgeInsets.fromLTRB(28, 24, 28, 24),
              child: SizedBox(
                width: double.infinity,
                height: 54,
                child: FilledButton(
                  onPressed: _isLast
                      ? _finish
                      : () => _controller.nextPage(
                            duration: const Duration(milliseconds: 300),
                            curve: Curves.easeOut,
                          ),
                  child: Text(
                    _isLast ? '시작하기' : '다음',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OnboardPage extends StatelessWidget {
  const _OnboardPage({
    required this.icon,
    required this.title,
    required this.desc,
  });

  final IconData icon;
  final String title;
  final String desc;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // 브랜드 그라데이션 원 안의 아이콘
          Container(
            width: 140,
            height: 140,
            alignment: Alignment.center,
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [AppColors.gradientTop, AppColors.gradientBottom],
              ),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 64, color: Colors.white),
          ),
          const SizedBox(height: 36),
          Text(
            title,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 23,
              fontWeight: FontWeight.w900,
              height: 1.35,
              color: AppColors.textStrong,
            ),
          ),
          const SizedBox(height: 14),
          Text(
            desc,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 14,
              height: 1.6,
              color: AppColors.textWeak,
            ),
          ),
        ],
      ),
    );
  }
}
