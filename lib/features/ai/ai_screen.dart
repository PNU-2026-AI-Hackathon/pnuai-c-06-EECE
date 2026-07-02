import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';

/// AI 메뉴 추천 — MVP는 규칙 기반 Mock (추후 LLM+RAG 교체)
class AiScreen extends ConsumerStatefulWidget {
  const AiScreen({super.key});

  @override
  ConsumerState<AiScreen> createState() => _AiScreenState();
}

class _AiScreenState extends ConsumerState<AiScreen> {
  final _controller = TextEditingController();
  String? _question;
  String? _answer;

  static const _presets = ['지금 제일 빨리 먹을 수 있는 곳', '5,000원 이하 메뉴', '매운 게 땡겨'];

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _ask(String question) {
    final lines = ref.read(cafeteriaLinesProvider).valueOrNull;
    String answer;
    if (lines == null || lines.isEmpty) {
      answer = '대기 데이터를 불러오는 중이에요. 잠시 후 다시 시도해 주세요.';
    } else {
      // Mock 규칙: 혼잡도 데이터 기반 최소 대기 라인 추천
      final fastest = [...lines]
        ..sort((a, b) => a.estimatedWaitMinutes.compareTo(b.estimatedWaitMinutes));
      final best = fastest.first;
      answer = '지금은 "${best.name}"이 가장 빨라요! '
          '대기 ${best.waitingCount}명, 약 ${best.estimatedWaitMinutes}분 예상이에요. '
          '오늘 메뉴는 ${best.todayMenu.join(", ")}입니다. '
          '\n\n(MVP Mock 응답 — 추후 LLM+RAG로 교체 예정)';
    }
    setState(() {
      _question = question;
      _answer = answer;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AI 메뉴 추천')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(
            controller: _controller,
            decoration: InputDecoration(
              hintText: '예: 지금 어디가 제일 빨라?',
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide.none,
              ),
              suffixIcon: IconButton(
                icon: const Icon(Icons.send),
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
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final p in _presets)
                ActionChip(label: Text(p), onPressed: () => _ask(p)),
            ],
          ),
          if (_question != null) ...[
            const SizedBox(height: 20),
            Align(
              alignment: Alignment.centerRight,
              child: Card(
                color: Theme.of(context).colorScheme.primaryContainer,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(_question!),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(_answer ?? ''),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
