/// 환경 설정 — Supabase 접속 정보.
///
/// 값을 넣는 방법 2가지 (권장 순):
///
/// 1) 실행 시 --dart-define (git에 안 올라감, 가장 안전)
///    flutter run \
///      --dart-define=SUPABASE_URL=https://xxxx.supabase.co \
///      --dart-define=SUPABASE_ANON_KEY=eyJhbGci...
///
/// 2) 아래 fallback 기본값에 직접 입력 (빠르지만 git 커밋 주의)
///
/// URL·anon key 둘 다 비어 있으면 앱은 자동으로 Mock 데이터로 동작한다.
/// (anon key는 클라이언트 공개용 키라 앱에 넣는 게 정상이며, 접근 제어는 RLS로 한다.)
class Env {
  static const supabaseUrl = String.fromEnvironment(
    'SUPABASE_URL',
    // 백엔드(조우진) 제공 프로젝트 URL. anon key와 함께 클라이언트에 넣어도 되는 공개 값.
    defaultValue: 'https://nnvqiigzlvgukvmrrama.supabase.co',
  );

  static const supabaseAnonKey = String.fromEnvironment(
    'SUPABASE_ANON_KEY',
    defaultValue:
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5udnFpaWd6bHZndWt2bXJyYW1hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI4OTUwMjEsImV4cCI6MjA5ODQ3MTAyMX0.3nqLjxXSiBHyAdh_6lZ_HPg4fyUiQtjPOhgNNtB8DQQ',
  );

  /// Supabase 접속 정보가 채워졌는가 → 데이터소스 자동 선택 기준
  static bool get useSupabase =>
      supabaseUrl.isNotEmpty && supabaseAnonKey.isNotEmpty;

  /// Gemini API 키 (무료 티어 — aistudio.google.com에서 발급)
  /// 실행: flutter run --dart-define=GEMINI_API_KEY=AIza...
  /// ⚠️ 클라이언트 내장 키는 해커톤 MVP용 — 정식 배포 시 서버(/api/ai/search) 경유로 전환.
  static const geminiApiKey = String.fromEnvironment(
    'GEMINI_API_KEY',
    defaultValue: '',
  );

  static bool get hasGemini => geminiApiKey.isNotEmpty;
}
