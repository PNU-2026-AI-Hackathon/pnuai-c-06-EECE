import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart' show AuthException;

import '../../app/providers.dart' show demoModeProvider;
import '../../app/theme.dart';
import 'auth_controller.dart';
import 'widgets/auth_text_field.dart';

/// 로그인 화면 — 카카오 로그인 전용 (가입+로그인 통합).
/// 카카오 OAuth 설정 전까지는 하단 "개발용 이메일 로그인" 폴백으로 테스트 가능.
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  bool _loading = false;
  String? _error;
  bool _showDevLogin = false;

  final _email = TextEditingController();
  final _password = TextEditingController();
  final _passwordFocus = FocusNode();

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _passwordFocus.dispose();
    super.dispose();
  }

  Future<void> _kakaoLogin() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ref.read(authControllerProvider).signInWithKakao();
      // 브라우저/카카오톡으로 이동 → 딥링크 복귀 시 라우터가 홈으로 보냄
    } on AuthException catch (e) {
      setState(() => _error = '카카오 로그인에 실패했어요: ${e.message}\n'
          '(백엔드 카카오 설정이 완료됐는지 확인해 주세요)');
    } catch (e) {
      setState(() => _error = '카카오 로그인에 실패했어요: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _devEmailLogin() async {
    // ── 마스터 계정: Supabase 없이 즉시 입장 (개발/시연용 백도어) ──
    if (_email.text.trim() == kMasterId &&
        _password.text == kMasterPassword) {
      ref.read(devSessionProvider.notifier).state = true;
      return; // isLoggedInProvider가 true가 되면서 라우터가 홈으로 보냄
    }

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ref
          .read(authControllerProvider)
          .signIn(_email.text.trim(), _password.text);
    } on AuthException catch (e) {
      setState(() => _error = switch (e.message) {
            final String m when m.contains('Invalid login credentials') =>
              '이메일 또는 비밀번호가 올바르지 않습니다.',
            _ => '로그인에 실패했어요: ${e.message}',
          });
    } catch (e) {
      setState(() => _error = '로그인에 실패했어요: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // ── 브랜드 영역 ──
                Center(
                  child: Container(
                    width: 84,
                    height: 84,
                    alignment: Alignment.center,
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          AppColors.gradientTop,
                          AppColors.gradientBottom,
                        ],
                      ),
                      shape: BoxShape.circle,
                    ),
                    child: const Text(
                      '밥',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 36,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'PNU 밥묵자',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textStrong,
                  ),
                ),
                const Text(
                  '부산대 학식 모바일 식권 · 실시간 웨이팅',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 13, color: AppColors.textWeak),
                ),
                const SizedBox(height: 48),
                // ── 카카오 로그인 (유일한 공식 진입점) ──
                SizedBox(
                  height: 54,
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFFFEE500), // 카카오 옐로
                      foregroundColor: const Color(0xFF191919),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(kRadiusButton),
                      ),
                    ),
                    onPressed: _loading ? null : _kakaoLogin,
                    child: _loading
                        ? const SizedBox(
                            height: 22,
                            width: 22,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.5,
                              color: Color(0xFF191919),
                            ),
                          )
                        : const Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              // 카카오 말풍선 심볼 (아이콘 대체)
                              Icon(Icons.chat_bubble, size: 20),
                              SizedBox(width: 8),
                              Text(
                                '카카오로 시작하기',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          ),
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  '카카오 계정 하나로 가입과 로그인이 한 번에 돼요',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 12, color: AppColors.textWeak),
                ),
                const SizedBox(height: 12),
                // 시연(Mock) 모드 — 로그인·서버 없이 가짜 데이터로 전체 둘러보기
                OutlinedButton.icon(
                  icon: const Icon(Icons.play_circle_outline, size: 18),
                  label: const Text('시연 모드로 둘러보기 (Mock)'),
                  onPressed: _loading
                      ? null
                      : () => ref.read(demoModeProvider.notifier).state = true,
                ),
                if (_error != null) ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.crowded.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      _error!,
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppColors.crowded,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 32),
                // ── 개발용 이메일 로그인 (카카오 설정 전 테스트 폴백) ──
                // TODO: 카카오 연동 확정 후 이 블록 전체 삭제
                Center(
                  child: TextButton(
                    onPressed: _loading
                        ? null
                        : () => setState(() => _showDevLogin = !_showDevLogin),
                    child: Text(
                      _showDevLogin ? '개발용 로그인 접기' : '개발용 이메일 로그인',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFFB4BCCA),
                      ),
                    ),
                  ),
                ),
                if (_showDevLogin) ...[
                  const SizedBox(height: 8),
                  AuthTextField(
                    controller: _email,
                    label: '아이디 또는 이메일 (개발용)',
                    icon: Icons.mail_outline,
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.next,
                    // 다음(탭) → 비밀번호 필드로 포커스 이동
                    onSubmitted: (_) => _passwordFocus.requestFocus(),
                    enabled: !_loading,
                  ),
                  const SizedBox(height: 12),
                  AuthTextField(
                    controller: _password,
                    focusNode: _passwordFocus,
                    label: '비밀번호',
                    icon: Icons.lock_outline,
                    obscure: true,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _devEmailLogin(),
                    enabled: !_loading,
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton(
                    onPressed: _loading ? null : _devEmailLogin,
                    child: const Text('이메일로 로그인 (개발용)'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
