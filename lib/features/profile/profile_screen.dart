import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';

/// 마이 — Mock 사용자 + 내 쿠폰 (추후 학교 이메일 인증 연동)
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final couponsAsync = ref.watch(couponsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('마이')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              leading: const CircleAvatar(child: Icon(Icons.person)),
              title: const Text('부산대 학생'),
              subtitle: const Text('정보컴퓨터공학부 · Mock 계정'),
              trailing: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.green.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: const Text(
                  '학번 인증됨',
                  style: TextStyle(
                    color: Colors.green,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text('내 쿠폰', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          couponsAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Text('오류: $e'),
            data: (coupons) => Column(
              children: [
                for (final c in coupons)
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.confirmation_num_outlined),
                      title: Text(c.title),
                      subtitle:
                          Text('${c.restaurantName} · ${c.condition}'),
                      trailing: Text(c.expiresText),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
