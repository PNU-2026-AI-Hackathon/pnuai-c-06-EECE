import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'app/app.dart';
import 'app/providers.dart';
import 'core/env.dart';
import 'core/notifications.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Supabase 접속 정보가 있을 때만 초기화. 없으면 Mock으로 동작.
  if (Env.useSupabase) {
    await Supabase.initialize(
      url: Env.supabaseUrl,
      publishableKey: Env.supabaseAnonKey,
    );
  }

  // 시스템 알림 초기화 (백그라운드 호출 알림용, 웹은 자동 무시)
  await NotificationService.init();

  // 저장된 설정 복원 (호출 알림 ON/OFF)
  final prefs = await SharedPreferences.getInstance();
  final callAlertEnabled = prefs.getBool('notify_enabled') ?? true;

  runApp(
    ProviderScope(
      overrides: [
        callAlertEnabledProvider.overrideWith((ref) => callAlertEnabled),
      ],
      child: const BapMukJaApp(),
    ),
  );
}
