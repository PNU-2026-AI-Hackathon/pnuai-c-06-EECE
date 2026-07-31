import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// 로컬(시스템) 알림 — 앱이 백그라운드에 있어도 잠금화면/상단바에 호출 알림 표시.
///
/// 범위: 앱 프로세스가 살아있는 동안 동작 (백그라운드 포함).
/// 앱이 완전히 종료된 상태의 푸시는 FCM(서버 발송)이 필요 — 추후 백엔드 연동.
/// 웹은 미지원 → 조용히 무시 (웹에선 스낵바가 담당).
class NotificationService {
  NotificationService._();

  static final _plugin = FlutterLocalNotificationsPlugin();
  static bool _ready = false;

  /// main()에서 1회 호출
  static Future<void> init() async {
    if (kIsWeb) return;
    try {
      const android = AndroidInitializationSettings('@mipmap/ic_launcher');
      const ios = DarwinInitializationSettings(
        requestAlertPermission: true,
        requestBadgePermission: true,
        requestSoundPermission: true,
      );
      await _plugin.initialize(
        const InitializationSettings(android: android, iOS: ios),
      );
      // Android 13+ 알림 권한 요청
      await _plugin
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.requestNotificationsPermission();
      _ready = true;
    } catch (_) {
      // 알림 초기화 실패는 앱 동작을 막지 않음 (스낵바 폴백 존재)
      _ready = false;
    }
  }

  /// 호출 알림 표시
  static Future<void> showCallAlert({
    required String lineName,
    required int queueNumber,
  }) async {
    if (kIsWeb || !_ready) return;
    try {
      await _plugin.show(
        queueNumber, // 같은 번호 중복 방지용 id
        '🍚 $lineName 호출!',
        '대기번호 $queueNumber번, 지금 배식대로 이동하세요.',
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'call_channel',
            '배식 호출 알림',
            channelDescription: '내 차례가 되면 알려드려요',
            importance: Importance.max,
            priority: Priority.high,
            category: AndroidNotificationCategory.reminder,
          ),
          iOS: DarwinNotificationDetails(
            presentAlert: true,
            presentSound: true,
            interruptionLevel: InterruptionLevel.timeSensitive,
          ),
        ),
      );
    } catch (_) {/* 무시 — 스낵바 폴백 */}
  }
}
