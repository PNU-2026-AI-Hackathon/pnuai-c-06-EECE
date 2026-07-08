import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../app/providers.dart' show demoModeProvider;
import '../../core/env.dart';

/// 인증 상태 스트림. Supabase 모드가 아니면 항상 "로그인됨"으로 취급해
/// Mock 시연 시 로그인 화면을 건너뛴다.
final authStateProvider = StreamProvider<AuthState?>((ref) {
  if (!Env.useSupabase) return const Stream<AuthState?>.empty();
  return Supabase.instance.client.auth.onAuthStateChange;
});

/// 현재 로그인 여부 (라우터 게이트에서 사용)
final isLoggedInProvider = Provider<bool>((ref) {
  if (!Env.useSupabase) return true; // Mock 빌드는 로그인 불필요
  if (ref.watch(demoModeProvider)) return true; // 시연(Mock) 모드
  if (ref.watch(devSessionProvider)) return true; // 마스터 로그인
  // authStateProvider를 구독해 로그인/로그아웃 시 재평가되게 함
  ref.watch(authStateProvider);
  return Supabase.instance.client.auth.currentSession != null;
});

/// ── 개발용 마스터 계정 ─────────────────────────────────────
/// 카카오/Supabase 설정 없이 개발자가 바로 들어갈 수 있는 백도어.
/// ⚠️ 시연·개발 전용 — 스토어 배포 전 반드시 이 블록과 관련 코드를 삭제할 것.
const kMasterId = 'pnumaster';
const kMasterPassword = 'bapmukja2026!';

/// 마스터 로그인 여부 (앱 재시작 시 초기화)
final devSessionProvider = StateProvider<bool>((ref) => false);

/// 카카오 OAuth 딥링크 — AndroidManifest·Info.plist에 등록돼 있고,
/// 백엔드가 Supabase 대시보드(Auth → URL Configuration)에도 같은 값을 등록해야 함.
const kakaoRedirectUri = 'io.pnubapmukja://login-callback';

/// 현재 로그인한 Supabase 사용자 (Mock/마스터 모드면 null)
/// 카카오 로그인 시 user_metadata에 닉네임(name)·프로필 사진(avatar_url)이 들어옴.
final currentUserProvider = Provider<User?>((ref) {
  if (!Env.useSupabase) return null;
  if (ref.watch(demoModeProvider)) return null; // 시연 모드는 Mock 사용자로 표시
  ref.watch(authStateProvider); // 로그인/로그아웃 시 재평가
  return Supabase.instance.client.auth.currentUser;
});

/// 인증 액션 — 카카오 OAuth가 기본, 이메일은 개발용 폴백
class AuthController {
  AuthController(this._client);
  final SupabaseClient _client;

  /// 카카오 로그인 (가입+로그인 통합 — 첫 로그인 시 자동 가입).
  /// 브라우저/카카오톡으로 나갔다가 딥링크로 복귀하면 세션이 생기고,
  /// onAuthStateChange → 라우터 게이트가 홈으로 보낸다.
  ///
  /// ⚠️ 백엔드 선행 작업 필요:
  ///  1) Kakao Developers 앱 등록 + REST API 키
  ///  2) Supabase Auth → Providers → Kakao 활성화 (키 입력)
  ///  3) Redirect URL에 [kakaoRedirectUri] 등록
  Future<void> signInWithKakao() async {
    await _client.auth.signInWithOAuth(
      OAuthProvider.kakao,
      // 모바일: 딥링크로 앱 복귀 / 웹: 현재 사이트 주소로 복귀.
      // 웹 테스트 시 포트 고정 필요: flutter run -d chrome --web-port 3000
      // → Supabase Redirect URLs에 http://localhost:3000 등록돼 있어야 함.
      redirectTo: kIsWeb ? Uri.base.origin : kakaoRedirectUri,
      // 이메일 동의항목 없이 요청 (비즈 앱 미전환 상태 대응).
      // ⚠️ 단, Supabase(GoTrue)가 서버 측에서 account_email을 기본 포함하는
      // 사례가 보고됨(KOE205 지속) — 그 경우 카카오 앱을 "개인개발자 비즈앱"으로
      // 전환해 account_email 동의항목을 켜는 것이 확실한 해결책.
      // 참고: github.com/supabase/supabase/issues/36878
      scopes: 'profile_nickname profile_image',
    );
  }

  /// (개발용 폴백) 이메일 로그인 — 카카오 설정 전 테스트용
  Future<void> signIn(String email, String password) async {
    await _client.auth.signInWithPassword(email: email, password: password);
  }

  Future<void> signOut() async => _client.auth.signOut();
}

final authControllerProvider = Provider<AuthController>(
  (ref) => AuthController(Supabase.instance.client),
);
