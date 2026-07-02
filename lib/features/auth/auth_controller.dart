import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/env.dart';

/// 인증 상태 스트림. Supabase 모드가 아니면 항상 "로그인됨"으로 취급해
/// Mock 시연 시 로그인 화면을 건너뛴다.
final authStateProvider = StreamProvider<AuthState?>((ref) {
  if (!Env.useSupabase) return Stream<AuthState?>.empty();
  return Supabase.instance.client.auth.onAuthStateChange;
});

/// 현재 로그인 여부 (라우터 게이트에서 사용)
final isLoggedInProvider = Provider<bool>((ref) {
  if (!Env.useSupabase) return true; // Mock 모드는 로그인 불필요
  // authStateProvider를 구독해 로그인/로그아웃 시 재평가되게 함
  ref.watch(authStateProvider);
  return Supabase.instance.client.auth.currentSession != null;
});

/// 이메일 로그인·회원가입·로그아웃 액션
class AuthController {
  AuthController(this._client);
  final SupabaseClient _client;

  Future<void> signIn(String email, String password) async {
    await _client.auth.signInWithPassword(email: email, password: password);
  }

  Future<void> signUp(String email, String password) async {
    await _client.auth.signUp(email: email, password: password);
  }

  Future<void> signOut() async => _client.auth.signOut();
}

final authControllerProvider = Provider<AuthController>(
  (ref) => AuthController(Supabase.instance.client),
);
