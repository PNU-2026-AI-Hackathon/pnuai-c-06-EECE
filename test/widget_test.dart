// 도메인 규칙 스모크 테스트
// (이 파일이 있으면 `flutter create .` 실행 시 기본 widget_test가 생성되지 않음)
import 'package:flutter_test/flutter_test.dart';
import 'package:pnu_bapmukja/core/formatters.dart';
import 'package:pnu_bapmukja/data/mock/mock_campus_data_source.dart';
import 'package:pnu_bapmukja/data/models/meal_ticket.dart';

void main() {
  test('won(): 천 단위 콤마', () {
    expect(won(5500), '5,500원');
    expect(won(12000), '12,000원');
  });

  test('식권 구매 = 대기열 자동 등록 (대기번호 발급 + 대기 인원 +1)', () {
    final ds = MockCampusDataSource(); // start() 안 함 — 타이머 없이 검증
    final before = ds.lines.firstWhere((l) => l.id == 'line_1f_jeongsik');

    final ticket = ds.purchaseTicket('line_1f_jeongsik');

    final after = ds.lines.firstWhere((l) => l.id == 'line_1f_jeongsik');
    expect(ticket.status, TicketStatus.waiting);
    expect(ticket.queueNumber, greaterThan(0));
    expect(after.waitingCount, before.waitingCount + 1);

    // 체크인 = 대기열 제거
    ds.checkIn(ticket.id);
    final done = ds.tickets.firstWhere((t) => t.id == ticket.id);
    expect(done.status, TicketStatus.used);
    ds.dispose();
  });
}
