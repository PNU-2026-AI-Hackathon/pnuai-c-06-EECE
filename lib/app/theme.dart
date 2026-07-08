import 'package:flutter/material.dart';

/// ── PNU 밥묵자 디자인 토큰 (수정계획서 목업 기준) ─────────────
/// 밝은 로열 블루 + 오렌지 액센트, 큰 라운드, 은은한 그림자
class AppColors {
  AppColors._();

  /// 부산대 공식 교색 (pusan.ac.kr 컬러시스템: #005BAA)
  static const pnuBlue = Color(0xFF005BAA);

  /// Primary = 교색 그대로 — "부산대 블루"가 앱의 얼굴
  static const primary = pnuBlue;

  /// 헤더 그라데이션 — 교색 기반 딥 네이비 → 클리어 블루
  static const gradientTop = Color(0xFF00417E);
  static const gradientBottom = Color(0xFF1B7ED2);

  /// CTA·강조 오렌지 (식사의 따뜻함 — 공대 지정색 #FFA500 톤)
  static const accent = Color(0xFFFF8A00);
  static const accentSoft = Color(0xFFFFF3E0);

  /// 혼잡도 3색 — '여유'는 부산대 공식 보조색 그린(#00A651)
  static const relaxed = Color(0xFF00A651);
  static const normal = Color(0xFFFF9800);
  static const crowded = Color(0xFFE53935);

  /// 배경/텍스트 — 옅은 블루그레이 배경 + 네이비 잉크 텍스트
  static const background = Color(0xFFF3F6FB);
  static const textStrong = Color(0xFF16243D);
  static const textWeak = Color(0xFF75809A);
}

/// 카드 공통 그림자 (교색 네이비 틴트 — 은은하게 뜬 느낌)
const kCardShadow = [
  BoxShadow(
    color: Color(0x12003A75),
    blurRadius: 16,
    offset: Offset(0, 4),
  ),
];

/// 라운드 값
const kRadiusCard = 20.0;
const kRadiusButton = 14.0;
const kRadiusPill = 999.0;

const pnuBlue = AppColors.pnuBlue; // 하위 호환

ThemeData buildAppTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    primary: AppColors.primary,
  );
  return ThemeData(
    useMaterial3: true,
    fontFamily: 'Pretendard',
    colorScheme: scheme,
    scaffoldBackgroundColor: AppColors.background,
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.background,
      foregroundColor: AppColors.textStrong,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(
        color: AppColors.textStrong,
        fontSize: 20,
        fontWeight: FontWeight.w800,
      ),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(kRadiusCard),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.primary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(kRadiusButton),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primary,
        side: const BorderSide(color: AppColors.primary),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(kRadiusButton),
        ),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white,
      height: 64,
      elevation: 0,
      indicatorColor: AppColors.primary.withValues(alpha: 0.10),
      labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
      iconTheme: WidgetStateProperty.resolveWith(
        (states) => IconThemeData(
          color: states.contains(WidgetState.selected)
              ? AppColors.primary
              : AppColors.textWeak,
        ),
      ),
      labelTextStyle: WidgetStateProperty.resolveWith(
        (states) => TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: states.contains(WidgetState.selected)
              ? AppColors.primary
              : AppColors.textWeak,
        ),
      ),
    ),
  );
}
