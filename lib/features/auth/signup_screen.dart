// ⚠️ 미사용 파일 (보관용) — 카카오 전용 인증으로 전환되며 라우트에서 제거됨.
// 카카오 OAuth는 첫 로그인 시 자동 가입되므로 별도 회원가입 화면이 필요 없다.
// 이메일 회원가입을 되살려야 할 경우 git 히스토리의 이전 버전을 참고할 것.
//
// (라우터에 등록되어 있지 않아 앱 번들에는 포함되지 않는다.)

import 'package:flutter/material.dart';

/// 사용되지 않음 — 카카오 전용 인증 전환으로 대체됨.
@Deprecated('카카오 OAuth 통합 가입으로 대체됨 (login_screen.dart 참고)')
class SignupScreen extends StatelessWidget {
  const SignupScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: Text('카카오 로그인으로 가입해 주세요.')),
    );
  }
}
