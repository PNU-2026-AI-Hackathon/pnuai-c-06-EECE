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
    required this.queueNo,
    this.qrToken,
  });

  final String id;
  final String lineId;
  final String status; // paid | called | used | expired
  final DateTime paidAt;

  /// 고정 대기번호 (은행 번호표 방식) — 학생 앱 표시 번호와 동일
  final int queueNo;
  final String? qrToken;
}

/// 라인 하나의 운영 현황 집계
class OperatorLineQueue {
  const OperatorLineQueue({
    this.waiting = const [],
    this.called = const [],
    this.servedToday = 0,
  });

  final List<OperatorTicket> waiting; // status=paid, 번호순 (맨 앞 = 다음 호출 대상)
  final List<OperatorTicket> called; // status=called (호출됨, 배식대 이동 중)
  final int servedToday; // 오늘 배식(used) 완료 수
}

/// 실서버 모드: tickets 테이블 전체를 Realtime 구독 → 라인별 대기열 집계.
/// 대기번호는 "오늘 그 라인 발급 순서"로 고정 (학생 앱과 동일 규칙) —
/// 앞사람이 빠져도 번호가 안 바뀌므로 운영자·학생 화면의 번호가 항상 일치한다.
/// (시연 모드에서는 빈 맵 — 운영자 화면이 Mock 시뮬레이션으로 대체됨)
final operatorQueuesProvider =
    StreamProvider<Map<String, OperatorLineQueue>>((ref) {
  if (!ref.watch(useSupabaseProvider)) {
    return Stream.value(const <String, OperatorLineQueue>{});
  }

  return Supabase.instance.client
      .from('tickets')
      .stream(primaryKey: ['id']).map((rows) {
    final now = DateTime.now();
    bool isToday(DateTime d) =>
        d.year == now.year && d.month == now.month && d.day == now.day;

    // 오늘 발급분만 라인별로 모음 (지난 날짜 티켓은 운영 화면과 무관)
    final byLine = <String, List<Map<String, dynamic>>>{};
    final paidLocalById = <String, DateTime>{};
    for (final t in rows) {
      final paidAt = (DateTime.tryParse(t['paid_at']?.toString() ?? '') ??
              DateTime.fromMillisecondsSinceEpoch(0))
          .toLocal();
      if (!isToday(paidAt)) continue;
      final lineId = t['dining_line_id']?.toString() ?? '';
      if (lineId.isEmpty) continue;
      paidLocalById[t['id'].toString()] = paidAt;
      (byLine[lineId] ??= []).add(t);
    }

    return {
      for (final entry in byLine.entries)
        entry.key: () {
          // 발급 순 정렬 → 고정 번호 부여 (1번부터)
          final sorted = entry.value
            ..sort((a, b) => paidLocalById[a['id'].toString()]!
                .compareTo(paidLocalById[b['id'].toString()]!));
          final tickets = [
            for (var i = 0; i < sorted.length; i++)
              OperatorTicket(
                id: sorted[i]['id'].toString(),
                lineId: entry.key,
                status: (sorted[i]['status'] as String?) ?? '',
                paidAt: paidLocalById[sorted[i]['id'].toString()]!,
                queueNo: i + 1,
                qrToken: sorted[i]['qr_token']?.toString(),
              ),
          ];
          return OperatorLineQueue(
            waiting: tickets.where((t) => t.status == 'paid').toList(),
            called: tickets.where((t) => t.status == 'called').toList(),
            servedToday: tickets.where((t) => t.status == 'used').length,
          );
        }(),
    };
  });
});
