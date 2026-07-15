import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../app/providers.dart';

/// 운영자용 티켓 뷰 (실서버 모드 전용)
class OperatorTicket {
  const OperatorTicket({
    required this.id,
    required this.lineId,
    required this.status,
    required this.paidAt,
    this.qrToken,
  });

  final String id;
  final String lineId;
  final String status; // paid | called | used | expired
  final DateTime paidAt;
  final String? qrToken;
}

/// 라인 하나의 운영 현황 집계
class OperatorLineQueue {
  const OperatorLineQueue({
    this.waiting = const [],
    this.called = const [],
    this.servedToday = 0,
  });

  final List<OperatorTicket> waiting; // status=paid, paid_at 순 (맨 앞 = 다음 배식)
  final List<OperatorTicket> called; // status=called (호출됨, 배식대 이동 중)
  final int servedToday; // 오늘 배식(used) 완료 수
}

/// 실서버 모드: tickets 테이블 전체를 Realtime 구독 → 라인별 대기열 집계.
/// 학생 앱의 대기번호 계산(paid_at 순 순번)과 동일한 규칙을 쓰므로
/// 운영자 화면의 순번과 학생 화면의 대기번호가 항상 일치한다.
/// (시연 모드에서는 빈 맵 — 운영자 화면이 Mock 시뮬레이션으로 대체됨)
final operatorQueuesProvider =
    StreamProvider<Map<String, OperatorLineQueue>>((ref) {
  if (!ref.watch(useSupabaseProvider)) {
    return Stream.value(const <String, OperatorLineQueue>{});
  }

  bool isToday(DateTime d) {
    final now = DateTime.now();
    return d.year == now.year && d.month == now.month && d.day == now.day;
  }

  return Supabase.instance.client
      .from('tickets')
      .stream(primaryKey: ['id']).map((rows) {
    final byLine = <String, List<OperatorTicket>>{};
    for (final t in rows) {
      final ticket = OperatorTicket(
        id: t['id'].toString(),
        lineId: t['dining_line_id']?.toString() ?? '',
        status: (t['status'] as String?) ?? '',
        // UTC → 로컬(KST) 변환 (오늘 배식 집계·정렬 기준)
        paidAt: (DateTime.tryParse(t['paid_at']?.toString() ?? '') ??
                DateTime.fromMillisecondsSinceEpoch(0))
            .toLocal(),
        qrToken: t['qr_token']?.toString(),
      );
      if (ticket.lineId.isEmpty) continue;
      (byLine[ticket.lineId] ??= []).add(ticket);
    }

    return {
      for (final entry in byLine.entries)
        entry.key: OperatorLineQueue(
          waiting: entry.value.where((t) => t.status == 'paid').toList()
            ..sort((a, b) => a.paidAt.compareTo(b.paidAt)),
          called: entry.value.where((t) => t.status == 'called').toList(),
          servedToday: entry.value
              .where((t) => t.status == 'used' && isToday(t.paidAt))
              .length,
        ),
    };
  });
});
