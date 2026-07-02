import 'package:flutter/material.dart';

/// 부산대 시그니처 블루 기반 Material 3 테마
const pnuBlue = Color(0xFF005BAC);

ThemeData buildAppTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: pnuBlue);
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: const Color(0xFFF6F7F9),
    appBarTheme: AppBarTheme(
      backgroundColor: const Color(0xFFF6F7F9),
      foregroundColor: scheme.onSurface,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(
        color: scheme.onSurface,
        fontSize: 20,
        fontWeight: FontWeight.w700,
      ),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      ),
    ),
    navigationBarTheme: const NavigationBarThemeData(
      backgroundColor: Colors.white,
      height: 64,
      labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
    ),
  );
}
