import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/meal_ticket.dart';
import '../models/remote_waiting.dart';

/// 커스텀 Next.js API 클라이언트 (백엔드 문서 6절 계약).
///
/// ⚠️ 현재 API 배포 전 상태(문서: "🚧 구현 진행 중, 배포주소 추후 공유").
///    baseUrl이 비어 있으면 각 메서드가 명확한 예외를 던진다.
///    배포되면 --dart-define=API_BASE_URL=https://xxx.vercel.app 만 넣으면 켜진다.
///
/// 인증: Supabase 로그인 세션의 accessToken(JWT)을 Bearer로 첨부 (문서 7절).
class ApiClient {
  ApiClient(this._client);
  final SupabaseClient _client;

  static const _baseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');

  bool get isReady => _baseUrl.isNotEmpty;

  Map<String, String> get _headers {
    final token = _client.auth.currentSession?.accessToken;
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Never _notReady() => throw StateError(
        '식권·웨이팅 API가 아직 배포되지 않았습니다.\n'
        'API_BASE_URL이 정해지면 --dart-define로 넣어주세요. (백엔드: 조우진)',
      );

  Future<Map<String, dynamic>> _post(String path, Map<String, dynamic> body) async {
    if (!isReady) _notReady();
    final res = await http.post(
      Uri.parse('$_baseUrl$path'),
      headers: _headers,
      body: jsonEncode(body),
    );
    if (res.statusCode >= 400) {
      throw http.ClientException('API $path 실패 (${res.statusCode}): ${res.body}');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// POST /api/tickets  {diningLineId} → {ticketId, qrToken, queueCount}
  Future<MealTicket> purchaseTicket(String diningLineId) async {
    final data = await _post('/api/tickets', {'diningLineId': diningLineId});
    return MealTicket(
      id: data['ticketId'].toString(),
      lineId: diningLineId,
      lineName: (data['lineName'] as String?) ?? '',
      menuName: (data['menuName'] as String?) ?? '',
      price: (data['price'] as num?)?.toInt() ?? 0,
      queueNumber: (data['queueNo'] as num?)?.toInt() ??
          (data['queueCount'] as num?)?.toInt() ??
          0,
      aheadCount: (data['queueCount'] as num?)?.toInt() ?? 0,
      status: TicketStatus.waiting,
      purchasedAt: DateTime.now(),
      qrToken: data['qrToken']?.toString(),
    );
  }

  /// GET /api/lines/{id}/status → {waitingCount, waitEstimateSec, level}
  /// (Realtime 구독(dining_lines stream)으로도 같은 정보를 받을 수 있어 보조용)
  Future<Map<String, dynamic>> lineStatus(String diningLineId) async {
    if (!isReady) _notReady();
    final res = await http.get(
      Uri.parse('$_baseUrl/api/lines/$diningLineId/status'),
      headers: _headers,
    );
    if (res.statusCode >= 400) {
      throw http.ClientException(
        'API /api/lines/$diningLineId/status 실패 (${res.statusCode}): ${res.body}',
      );
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// POST /api/tickets/verify  {qrToken} → {valid, status}
  Future<void> verifyTicket(String qrToken) async {
    await _post('/api/tickets/verify', {'qrToken': qrToken});
  }

  /// POST /api/tickets/cancel  {ticketId} → {ok}
  /// 호출 전(paid) 식권만 취소 가능 — 검증은 서버가 (본인 소유·상태 확인)
  Future<void> cancelTicket(String ticketId) async {
    await _post('/api/tickets/cancel', {'ticketId': ticketId});
  }

  /// POST /api/waitings  {restaurantId} → {waitingId, queueNo}
  Future<RemoteWaiting> joinWaiting(String restaurantId) async {
    final data = await _post('/api/waitings', {'restaurantId': restaurantId});
    return RemoteWaiting(
      id: data['waitingId'].toString(),
      restaurantId: restaurantId,
      restaurantName: (data['restaurantName'] as String?) ?? '',
      number: (data['queueNo'] as num?)?.toInt() ?? 0,
      teamsAhead: (data['teamsAhead'] as num?)?.toInt() ?? 0,
      status: WaitingStatus.waiting,
      joinedAt: DateTime.now(),
    );
  }

  /// POST /api/ai/search  {query} → {answer, menus}
  Future<String> aiSearch(String query) async {
    final data = await _post('/api/ai/search', {'query': query});
    return (data['answer'] as String?) ?? '';
  }
}
