# 팀원 배포 가이드 (PNU 밥묵자)

앱을 팀원에게 공유하는 3가지 방법 — 쉬운 순서대로.

## 방법 1. 웹 배포 (가장 쉬움 — 링크만 공유) ✅ 권장

```bash
flutter build web --release
```

`build/web` 폴더가 생김. 이걸 정적 호스팅에 올리면 끝:

- **Vercel**: vercel.com 로그인 → New Project → `build/web` 폴더 드래그&드롭
  (또는 `npm i -g vercel && cd build/web && vercel --prod`)
- **Netlify**: app.netlify.com/drop 에 `build/web` 폴더 드래그&드롭

⚠️ 배포된 주소(예: `https://pnu-bapmukja.vercel.app`)에서 **카카오 로그인**을 쓰려면
백엔드에 그 주소를 Supabase Redirect URLs에 추가 요청해야 함.
로그인 없이 보여줄 거면 **"시연 모드로 둘러보기"** 버튼으로 충분 — 추가 설정 불필요.

## 방법 2. Android APK (실기기 설치)

```bash
flutter build apk --release
```

생성 위치: `build/app/outputs/flutter-apk/app-release.apk`
→ 카톡/드라이브로 파일 공유 → 팀원 폰에서 설치
(설치 시 "출처를 알 수 없는 앱" 허용 필요 — 정상, 서명 안 된 개발 빌드라서)

카카오 로그인은 딥링크가 이미 설정돼 있어 APK에서 바로 동작함.

## 방법 3. 소스 공유 (개발 팀원용)

```bash
git clone <repo> && cd pnu_bapmukja
flutter pub get
flutter run                      # 에뮬레이터/실기기
flutter run -d chrome --web-port 3000   # 웹 (카카오 로그인 테스트 시 포트 고정)
```

## 배포 전 체크리스트

- [ ] `flutter analyze` 통과
- [ ] `flutter pub get` 후 Pretendard 폰트 적용 확인
- [ ] 시연 모드 ON/OFF, 데모 초기화 동작 확인
- [ ] (외부 공유 시) 개발용 이메일 로그인·마스터 계정 노출 여부 판단
      — 마스터 계정: `pnumaster / bapmukja2026!` (auth_controller.dart)
- [ ] 웹 배포 시 카카오 로그인 필요하면 배포 URL을 백엔드에 전달
