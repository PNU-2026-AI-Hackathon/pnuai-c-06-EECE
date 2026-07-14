import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import 'operator_providers.dart';

/// 운영자 대시보드 — 실서버 모드.
///
/// · tickets 테이블 Realtime 구독 → 라인별 실제 대기열 표시
/// · "QR 스캔 · 배식 완료" = 대기열 맨 앞 티켓의 qr_token으로 verify API 호출
///   (카메라 스캔(mobile_scanner) 연동 전까지 동일 효과의 시연 버튼)
/// · 자동 운영 = 일정 간격으로 맨 앞 티켓을 자동 verify (배식 속도 시뮬레이션)
/// · 처리 결과는 Realtime으로 학생 앱에 즉시 반영된다.
class OperatorLiveView extends ConsumerStatefulWidget {
  const OperatorLiveView({super.key});

  @override
  ConsumerState<OperatorLiveView> createState() => _OperatorLiveViewState();
}

class _OperatorLiveViewState extends ConsumerState<OperatorLiveView> {
  String? _selectedLineId;
  bool _busy = false;

  /// 자동 운영 — 배식 간격마다 맨 앞 티켓을 자동 verify
  bool _autoMode = false;
  Timer? _autoTimer;
  static const _autoInterval = Duration(seconds: 6);

  @override
  void dispose() {
    _autoTimer?.cancel();
    super.dispose();
  }

  void _toggleAuto(bool on) {
    setState(() => _autoMode = on);
    _autoTimer?.cancel();
    if (on) {
      _autoTimer = Timer.periodic(_autoInterval, (_) => _autoTick());
      ScaffoldMessenger.of(context)
        ..clearSnackBars()
        ..showSnackBar(
          const SnackBar(
            content: Text('자동 운영 시작 — 배식 간격마다 맨 앞 식권을 자동 처리합니다.'),
          ),
        );
    }
  }

  Future<void> _autoTick() async {
    if (!mounted || _busy) return;
    final queue = _currentQueue();
    if (queue == null || queue.waiting.isEmpty) {
      _autoTimer?.cancel();
      if (mounted) setState(() => _autoMode = false);
      return;
    }
    await _verifyHead(queue, silent: true);
  }

  OperatorLineQueue? _currentQueue() {
    final queues = ref.read(operatorQueuesProvider).valueOrNull;
    final id = _selectedLineId;
    if (queues == null || id == null) return null;
    return queues[id];
  }

  /// 대기열 맨 앞 티켓 verify — 실서비스의 "QR 스캔"과 동일한 서버 호출
  Future<void> _verifyHead(OperatorLineQueue queue, {bool silent = false}) async {
    if (queue.waiting.isEmpty || _busy) return;
    final head = queue.waiting.first;
    final token = head.qrToken;
    final messenger = ScaffoldMessenger.of(context);

    if (token == null || token.isEmpty) {
      messenger.showSnackBar(
        const SnackBar(content: Text('맨 앞 식권에 qr_token이 없습니다 — 백엔드 확인 필요')),
      );
      return;
    }

    setState(() => _busy = true);
    try {
      await ref.read(apiClientProvider).verifyTicket(token);
      if (!silent && mounted) {
        messenger
          ..clearSnackBars()
          ..showSnackBar(
            const SnackBar(
              backgroundColor: AppColors.relaxed,
              behavior: SnackBarBehavior.floating,
              content: Text(
                '✅ 배식 완료 — 학생 앱에 실시간 반영됩니다.',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
            ),
          );
      }
    } catch (e) {
      if (mounted) {
        messenger
          ..clearSnackBars()
          ..showSnackBar(
            SnackBar(
              backgroundColor: AppColors.crowded,
              content: Text('검증 실패: $e', maxLines: 3),
            ),
          );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final linesAsync = ref.watch(cafeteriaLinesProvider);
    final queues =
        ref.watch(operatorQueuesProvider).valueOrNull ?? const <String, OperatorLineQueue>{};

    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Text('운영자 대시보드'),
            SizedBox(width: 8),
            _LiveBadge(),
          ],
        ),
      ),
      body: linesAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text('라인 정보를 불러오지 못했습니다.\n$e', textAlign: TextAlign.center),
          ),
        ),
        data: (lines) {
          if (lines.isEmpty) {
            return const Center(child: Text('등록된 배식 라인이 없습니다.'));
          }
          if (_selectedLineId == null ||
              !lines.any((l) => l.id == _selectedLineId)) {
            _selectedLineId = lines.first.id;
          }
          final selectedIndex =
              lines.indexWhere((l) => l.id == _selectedLineId);
          final queue = queues[_selectedLineId] ?? const OperatorLineQueue();

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
            children: [
              // ── 라인 선택 ──
              SizedBox(
                height: 40,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: lines.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (_, i) => ChoiceChip(
                    label: Text(lines[i].name),
                    selected: selectedIndex == i,
                    selectedColor: AppColors.primary,
                    labelStyle: TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 13,
                      color: selectedIndex == i
                          ? Colors.white
                          : AppColors.textStrong,
                    ),
                    onSelected: (_) =>
                        setState(() => _selectedLineId = lines[i].id),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              // ── 실시간 현황 카드 ──
              Container(
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [AppColors.gradientTop, AppColors.gradientBottom],
                  ),
                  borderRadius: BorderRadius.circular(kRadiusCard),
                  boxShadow: kCardShadow,
                ),
                padding: const EdgeInsets.all(20),
                child: Row(
                  children: [
                    _Stat(label: '대기', value: '${queue.waiting.length}명'),
                    _statDivider,
                    _Stat(label: '호출됨', value: '${queue.called.length}명'),
                    _statDivider,
                    _Stat(label: '오늘 배식', value: '${queue.servedToday}'),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              // ── 자동 운영 모드 ──
              Container(
                decoration: BoxDecoration(
                  color: _autoMode ? AppColors.accentSoft : Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: _autoMode ? Border.all(color: AppColors.accent) : null,
                  boxShadow: kCardShadow,
                ),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                child: Row(
                  children: [
                    Icon(
                      _autoMode ? Icons.autorenew : Icons.autorenew_outlined,
                      size: 22,
                      color: _autoMode ? AppColors.accent : AppColors.textWeak,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _autoMode ? '자동 운영 중 (실서버)' : '자동 운영 모드',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w800,
                              color: _autoMode
                                  ? AppColors.accent
                                  : AppColors.textStrong,
                            ),
                          ),
                          const Text(
                            '배식 간격마다 맨 앞 식권 자동 처리 → 학생 앱 실시간 반영',
                            style: TextStyle(
                              fontSize: 11,
                              color: AppColors.textWeak,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Switch(
                      value: _autoMode,
                      activeThumbColor: AppColors.accent,
                      onChanged: queue.waiting.isEmpty && !_autoMode
                          ? null
                          : _toggleAuto,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              // ── QR 스캔(배식 완료) 버튼 ──
              SizedBox(
                height: 52,
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.accent,
                  ),
                  icon: _busy
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.4,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.qr_code_scanner),
                  label: Text(_busy ? '처리 중...' : 'QR 스캔 · 배식 완료'),
                  onPressed: (queue.waiting.isEmpty || _busy || _autoMode)
                      ? null
                      : () => _verifyHead(queue),
                ),
              ),
              const SizedBox(height: 20),
              // ── 대기열 (실제 티켓, 학생 대기번호와 동일 순번) ──
              const Text(
                '대기열',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                  color: AppColors.textStrong,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(kRadiusCard),
                  boxShadow: kCardShadow,
                ),
                padding: const EdgeInsets.all(12),
                child: queue.waiting.isEmpty
                    ? const Padding(
                        padding: EdgeInsets.all(12),
                        child: Text(
                          '대기 중인 식권이 없습니다.\n학생 앱에서 구매하면 실시간으로 표시됩니다.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 13,
                            color: AppColors.textWeak,
                            height: 1.5,
                          ),
                        ),
                      )
                    : Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          for (final (i, _) in queue.waiting.take(20).indexed)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 6,
                              ),
                              decoration: BoxDecoration(
                                color: i == 0
                                    ? AppColors.accentSoft
                                    : const Color(0xFFF3F6FB),
                                borderRadius:
                                    BorderRadius.circular(kRadiusPill),
                                border: i == 0
                                    ? Border.all(color: AppColors.accent)
                                    : null,
                              ),
                              child: Text(
                                i == 0 ? '${i + 1} 다음' : '${i + 1}',
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w800,
                                  color: i == 0
                                      ? AppColors.accent
                                      : AppColors.textStrong,
                                ),
                              ),
                            ),
                          if (queue.waiting.length > 20)
                            Padding(
                              padding: const EdgeInsets.all(6),
                              child: Text(
                                '외 ${queue.waiting.length - 20}명',
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.textWeak,
                                ),
                              ),
                            ),
                        ],
                      ),
              ),
              const SizedBox(height: 16),
              const Text(
                '※ 실서버 모드 — 이 화면의 처리가 학생 앱에 실시간 반영됩니다.\n'
                '카메라 QR 스캔(mobile_scanner)과 자동 다음 호출(서버 called 전이)은 연동 예정.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 11, color: AppColors.textWeak),
              ),
            ],
          );
        },
      ),
    );
  }
}

const _statDivider = SizedBox(
  height: 48,
  child: VerticalDivider(color: Colors.white24, width: 1),
);

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
            label,
            style: const TextStyle(color: Colors.white70, fontSize: 12),
          ),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 34,
              fontWeight: FontWeight.w900,
              height: 1.2,
            ),
          ),
        ],
      ),
    );
  }
}

class _LiveBadge extends StatelessWidget {
  const _LiveBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: AppColors.relaxed.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(kRadiusPill),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.circle, size: 8, color: AppColors.relaxed),
          SizedBox(width: 4),
          Text(
            'LIVE',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w800,
              color: AppColors.relaxed,
            ),
          ),
        ],
      ),
    );
  }
}
