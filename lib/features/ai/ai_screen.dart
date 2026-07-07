import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../data/repositories/ai_repository.dart';

/// AI 메뉴 추천 — AiRepository 계약 기반 (Mock ↔ 서버 자동 전환)
class AiScreen extends ConsumerStatefulWidget {
  const AiScreen({super.key});

  @override
  ConsumerState<AiScreen> createState() => _AiScreenState();
}

class _ChatMessage {
  final String text;
  final bool isUser;
  final AiRecommendation? recommendation;
  const _ChatMessage(this.text, {required this.isUser, this.recommendation});
}

class _AiScreenState extends ConsumerState<AiScreen> {
  final _controller = TextEditingController();
  final _messages = <_ChatMessage>[];
  bool _loading = false;

  static const _presets = ['지금 제일 빨리 먹을 수 있는 곳', '5,000원 이하 메뉴', '매운 게 땡겨'];

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _ask(String question) async {
    if (_loading) return;
    setState(() {
      _messages.add(_ChatMessage(question, isUser: true));
      _loading = true;
    });
    _controller.clear();

    try {
      final lines = ref.read(cafeteriaLinesProvider).valueOrNull ?? const [];
      final result = await ref
          .read(aiRepositoryProvider)
          .ask(question, lines: lines);
      if (!mounted) return;
      setState(() {
        _messages.add(
          _ChatMessage(result.answer, isUser: false, recommendation: result),
        );
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _messages.add(_ChatMessage('추천에 실패했어요: $e', isUser: false));
      });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AI 메뉴 추천')),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_messages.isEmpty) const _EmptyGuide(),
                for (final m in _messages) _ChatBubble(message: m),
                if (_loading)
                  const Padding(
                    padding: EdgeInsets.all(12),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          // 프리셋 칩 + 입력바
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
              child: Column(
                children: [
                  SizedBox(
                    height: 36,
                    child: ListView.separated(
                      scrollDirection: Axis.horizontal,
                      itemCount: _presets.length,
                      separatorBuilder: (_, __) => const SizedBox(width: 8),
                      itemBuilder: (_, i) => ActionChip(
                        label: Text(
                          _presets[i],
                          style: const TextStyle(fontSize: 12),
                        ),
                        backgroundColor: Colors.white,
                        shape: const StadiumBorder(
                          side: BorderSide(color: Color(0xFFDDE4EE)),
                        ),
                        onPressed: () => _ask(_presets[i]),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _controller,
                    decoration: InputDecoration(
                      hintText: '"오늘 매콤한 거 땡기는 거"',
                      filled: true,
                      fillColor: Colors.white,
                      contentPadding:
                          const EdgeInsets.symmetric(horizontal: 18),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(kRadiusPill),
                        borderSide: BorderSide.none,
                      ),
                      suffixIcon: IconButton(
                        icon: const Icon(Icons.send, color: AppColors.primary),
                        onPressed: () {
                          if (_controller.text.trim().isNotEmpty) {
                            _ask(_controller.text.trim());
                          }
                        },
                      ),
                    ),
                    onSubmitted: (v) {
                      if (v.trim().isNotEmpty) _ask(v.trim());
                    },
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// 첫 진입 안내
class _EmptyGuide extends StatelessWidget {
  const _EmptyGuide();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 40),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(kRadiusCard),
        boxShadow: kCardShadow,
      ),
      child: const Column(
        children: [
          CircleAvatar(
            radius: 24,
            backgroundColor: AppColors.primary,
            child: Text(
              'AI',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          SizedBox(height: 12),
          Text(
            '뭐 먹을지 고민되면 물어보세요!',
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w800,
              color: AppColors.textStrong,
            ),
          ),
          SizedBox(height: 4),
          Text(
            '실시간 대기 현황과 오늘 메뉴를 기준으로\n가장 빠르고 맛있는 선택을 추천해요.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: AppColors.textWeak),
          ),
        ],
      ),
    );
  }
}

/// 채팅 말풍선 — 추천에 lineId가 있으면 "구매하러 가기" 버튼 노출
class _ChatBubble extends StatelessWidget {
  const _ChatBubble({required this.message});

  final _ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final rec = message.recommendation;
    return Align(
      alignment:
          message.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.78,
        ),
        decoration: BoxDecoration(
          color: message.isUser ? AppColors.primary : Colors.white,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(message.isUser ? 16 : 4),
            bottomRight: Radius.circular(message.isUser ? 4 : 16),
          ),
          boxShadow: message.isUser ? null : kCardShadow,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              message.text,
              style: TextStyle(
                fontSize: 14,
                height: 1.45,
                color:
                    message.isUser ? Colors.white : AppColors.textStrong,
              ),
            ),
            if (rec?.lineId != null) ...[
              const SizedBox(height: 8),
              FilledButton.icon(
                style: FilledButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                ),
                icon: const Icon(Icons.confirmation_num_outlined, size: 16),
                label: const Text('홈에서 식권 구매하기'),
                onPressed: () => context.go('/home'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
