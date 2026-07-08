import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../env.dart';

/// 공통 에러 화면 — 재시도 + (Supabase 모드) 시연 모드 폴백 제안.
/// 시연 중 서버/네트워크 장애가 나도 데모가 끊기지 않게 하는 안전망.
class ErrorRetryView extends ConsumerWidget {
  const ErrorRetryView({
    super.key,
    required this.onRetry,
    this.message,
  });

  final VoidCallback onRetry;
  final String? message;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final demoAvailable = Env.useSupabase && !ref.watch(demoModeProvider);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: AppColors.crowded.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(kRadiusPill),
              ),
              child: const Icon(
                Icons.wifi_off_rounded,
                color: AppColors.crowded,
                size: 34,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              '데이터를 불러오지 못했어요',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: AppColors.textStrong,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              message ?? '네트워크 상태를 확인하고 다시 시도해 주세요.',
              textAlign: TextAlign.center,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 13, color: AppColors.textWeak),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('다시 시도'),
              onPressed: onRetry,
            ),
            if (demoAvailable)
              TextButton(
                onPressed: () =>
                    ref.read(demoModeProvider.notifier).state = true,
                child: const Text(
                  '시연 모드(Mock)로 계속 보기',
                  style: TextStyle(fontSize: 13),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
