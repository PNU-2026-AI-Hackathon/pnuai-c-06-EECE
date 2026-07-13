import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';

/// 운영자 대시보드 (Mock) — 식당 관계자 협의·시연용.
/// 학생 앱의 반대편: 대기열 확인 → 호출 → QR 검증 → 메뉴/품절 관리.
/// 전부 로컬 Mock 상태로 동작 (실서버 연동은 백엔드 운영자 API 이후).
class OperatorScreen extends ConsumerStatefulWidget {
  const OperatorScreen({super.key});

  @override
  ConsumerState<OperatorScreen> createState() => _OperatorScreenState();
}

/// 라인별 운영 상태 (로컬 Mock)
class _OpLine {
  _OpLine({
    required this.id,
    required this.name,
    required this.menu,
    required this.queue,
    required this.nowServing,
  });

  final String id;
  final String name;
  List<String> menu;
  final List<int> queue; // 대기 중인 번호들
  int nowServing; // 현재 호출된 번호 (0 = 없음)
  bool soldOut = false;
  int servedCount = 0; // 오늘 검증(배식) 완료 수
}

class _OperatorScreenState extends ConsumerState<OperatorScreen> {
  final _random = Random();
  List<_OpLine>? _lines;
  int _selected = 0;

  /// 자동 운영 모드 — 배식 속도(간격)에 맞춰 자동으로
  /// [배식 완료 → 다음 번호 호출(=학생 앱 알림)]을 반복
  bool _autoMode = false;
  Timer? _autoTimer;
  static const _autoInterval = Duration(seconds: 4); // 시연용 배식 간격

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
            content: Text('자동 운영 시작 — 자리가 나면 다음 번호가 자동 호출·알림됩니다.'),
          ),
        );
    }
  }

  /// 자동 운영 1틱: 현재 호출자 배식 완료 → 다음 번호 호출
  void _autoTick() {
    if (!mounted) return;
    final line = _line;
    if (line.soldOut || line.queue.isEmpty) {
      // 대기열 소진/품절 시 자동 종료
      _autoTimer?.cancel();
      setState(() => _autoMode = false);
      return;
    }
    setState(() {
      if (line.nowServing != 0) line.servedCount++; // 자리 비워짐
      line.nowServing = line.queue.removeAt(0); // 다음 번호 호출 → 학생 앱 알림
    });
  }

  /// 학생 앱의 현재 대기 현황을 스냅샷으로 가져와 시드
  void _seedIfNeeded() {
    if (_lines != null) return;
    final appLines = ref.read(cafeteriaLinesProvider).valueOrNull ?? [];
    _lines = [
      for (final l in appLines)
        _OpLine(
          id: l.id,
          name: l.name,
          menu: List.of(l.todayMenu),
          nowServing: 30 + _random.nextInt(40),
          queue: [],
        ),
    ];
    for (final ol in _lines!) {
      final appLine =
          appLines.firstWhere((l) => l.id == ol.id);
      // 현재 호출 번호 다음부터 대기 인원만큼 번호 생성
      ol.queue.addAll(
        List.generate(appLine.waitingCount, (i) => ol.nowServing + 1 + i),
      );
      ol.servedCount = 80 + _random.nextInt(120);
    }
    if (_lines!.isEmpty) {
      // 데이터 로딩 전 폴백
      _lines = [
        _OpLine(
          id: 'demo',
          name: '1층 정식',
          menu: const ['제육볶음', '미역국', '배추김치'],
          nowServing: 42,
          queue: List.generate(12, (i) => 43 + i),
        ),
      ];
    }
  }

  _OpLine get _line => _lines![_selected];

  /// 다음 번호 호출
  void _callNext() {
    if (_line.queue.isEmpty) return;
    setState(() => _line.nowServing = _line.queue.removeAt(0));
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(
        SnackBar(
          backgroundColor: AppColors.accent,
          behavior: SnackBarBehavior.floating,
          content: Text(
            '🔔 ${_line.nowServing}번 호출! (학생 앱으로 푸시 알림 발송)',
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
        ),
      );
  }

  /// QR 검증 시뮬레이션
  void _scanQr() {
    final ok = _line.nowServing > 0;
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        icon: Icon(
          ok ? Icons.check_circle : Icons.error_outline,
          color: ok ? AppColors.relaxed : AppColors.crowded,
          size: 44,
        ),
        title: Text(ok ? 'QR 검증 성공' : '호출된 번호 없음'),
        content: Text(
          ok
              ? '대기번호 ${_line.nowServing}번 · ${_line.name}\n'
                  '유효한 식권입니다. 배식을 진행하세요.'
              : '먼저 "다음 번호 호출"을 눌러주세요.',
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 13, height: 1.5),
        ),
        actions: [
          FilledButton(
            onPressed: () {
              Navigator.pop(dialogContext);
              if (ok) {
                setState(() {
                  _line.servedCount++;
                  _line.nowServing = 0; // 배식 완료 → 다음 호출 대기
                });
              }
            },
            child: Text(ok ? '배식 완료 처리' : '확인'),
          ),
        ],
      ),
    );
  }

  /// 오늘 메뉴 수정
  Future<void> _editMenu() async {
    final controller = TextEditingController(text: _line.menu.join(', '));
    final result = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text('${_line.name} 오늘 메뉴'),
        content: TextField(
          controller: controller,
          maxLines: 3,
          decoration: const InputDecoration(
            hintText: '쉼표로 구분해 입력',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, controller.text),
            child: const Text('저장'),
          ),
        ],
      ),
    );
    if (result != null && result.trim().isNotEmpty) {
      setState(() {
        _line.menu = result
            .split(',')
            .map((s) => s.trim())
            .where((s) => s.isNotEmpty)
            .toList();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    _seedIfNeeded();
    final line = _line;

    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Text('운영자 대시보드'),
            SizedBox(width: 8),
            _MockBadge(),
          ],
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          // ── 라인 선택 ──
          SizedBox(
            height: 40,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: _lines!.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) => ChoiceChip(
                label: Text(_lines![i].name),
                selected: _selected == i,
                selectedColor: AppColors.primary,
                labelStyle: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                  color: _selected == i ? Colors.white : AppColors.textStrong,
                ),
                onSelected: (_) => setState(() => _selected = i),
              ),
            ),
          ),
          const SizedBox(height: 14),
          // ── 현재 호출/대기 현황 카드 ──
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
                Expanded(
                  child: Column(
                    children: [
                      const Text(
                        '현재 호출',
                        style: TextStyle(color: Colors.white70, fontSize: 12),
                      ),
                      Text(
                        line.nowServing == 0 ? '—' : '${line.nowServing}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 40,
                          fontWeight: FontWeight.w900,
                          height: 1.2,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  width: 1,
                  height: 48,
                  color: Colors.white.withValues(alpha: 0.25),
                ),
                Expanded(
                  child: Column(
                    children: [
                      const Text(
                        '대기',
                        style: TextStyle(color: Colors.white70, fontSize: 12),
                      ),
                      Text(
                        '${line.queue.length}명',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 40,
                          fontWeight: FontWeight.w900,
                          height: 1.2,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  width: 1,
                  height: 48,
                  color: Colors.white.withValues(alpha: 0.25),
                ),
                Expanded(
                  child: Column(
                    children: [
                      const Text(
                        '오늘 배식',
                        style: TextStyle(color: Colors.white70, fontSize: 12),
                      ),
                      Text(
                        '${line.servedCount}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 40,
                          fontWeight: FontWeight.w900,
                          height: 1.2,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          // ── 자동 운영 모드 (핵심 컨셉: 자리가 나면 자동 호출·알림) ──
          Container(
            decoration: BoxDecoration(
              color: _autoMode ? AppColors.accentSoft : Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: _autoMode
                  ? Border.all(color: AppColors.accent)
                  : null,
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
                        _autoMode ? '자동 운영 중' : '자동 운영 모드',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                          color: _autoMode
                              ? AppColors.accent
                              : AppColors.textStrong,
                        ),
                      ),
                      const Text(
                        '배식 완료 시 다음 번호 자동 호출 → 학생 앱 알림',
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
                  onChanged: line.queue.isEmpty && !_autoMode
                      ? null
                      : _toggleAuto,
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          // ── 수동 액션 버튼 (자동 모드 중엔 비활성) ──
          Row(
            children: [
              Expanded(
                child: SizedBox(
                  height: 52,
                  child: FilledButton.icon(
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.accent,
                    ),
                    icon: const Icon(Icons.campaign),
                    label: const Text('다음 번호 호출'),
                    onPressed:
                        (line.queue.isEmpty || _autoMode) ? null : _callNext,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: SizedBox(
                  height: 52,
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.qr_code_scanner),
                    label: const Text('QR 검증'),
                    onPressed: _scanQr,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          // ── 대기열 목록 ──
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
            child: line.queue.isEmpty
                ? const Padding(
                    padding: EdgeInsets.all(12),
                    child: Text(
                      '대기 중인 번호가 없습니다.',
                      textAlign: TextAlign.center,
                      style:
                          TextStyle(fontSize: 13, color: AppColors.textWeak),
                    ),
                  )
                : Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final (i, n) in line.queue.take(20).indexed)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: i == 0
                                ? AppColors.accentSoft
                                : const Color(0xFFF3F6FB),
                            borderRadius: BorderRadius.circular(kRadiusPill),
                            border: i == 0
                                ? Border.all(color: AppColors.accent)
                                : null,
                          ),
                          child: Text(
                            i == 0 ? '$n 다음' : '$n',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w800,
                              color: i == 0
                                  ? AppColors.accent
                                  : AppColors.textStrong,
                            ),
                          ),
                        ),
                      if (line.queue.length > 20)
                        Padding(
                          padding: const EdgeInsets.all(6),
                          child: Text(
                            '외 ${line.queue.length - 20}명',
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.textWeak,
                            ),
                          ),
                        ),
                    ],
                  ),
          ),
          const SizedBox(height: 20),
          // ── 메뉴/운영 관리 ──
          const Text(
            '메뉴 · 운영 관리',
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
            child: Material(
              color: Colors.transparent,
              child: Column(
              children: [
                ListTile(
                  dense: true,
                  leading: const Icon(Icons.restaurant_menu, size: 22),
                  title: Text(
                    line.menu.join(' · '),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  trailing: TextButton(
                    onPressed: _editMenu,
                    child: const Text('수정'),
                  ),
                ),
                const Divider(height: 1, indent: 52, color: Color(0xFFF0F2F7)),
                ListTile(
                  dense: true,
                  leading: const Icon(Icons.block, size: 22),
                  title: const Text(
                    '품절 / 조기 마감',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  trailing: Switch(
                    value: line.soldOut,
                    activeThumbColor: AppColors.crowded,
                    onChanged: (v) => setState(() => line.soldOut = v),
                  ),
                ),
              ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            '※ 시연용 Mock 화면입니다. 실제 운영 시 학생 앱과 실시간 연동되며,\n'
            '호출 시 해당 학생에게 푸시 알림이 발송됩니다.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11, color: AppColors.textWeak),
          ),
        ],
      ),
    );
  }
}

class _MockBadge extends StatelessWidget {
  const _MockBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: AppColors.accentSoft,
        borderRadius: BorderRadius.circular(kRadiusPill),
      ),
      child: const Text(
        '시연용',
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w800,
          color: AppColors.accent,
        ),
      ),
    );
  }
}
