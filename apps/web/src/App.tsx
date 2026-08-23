import {
  Navigate,
  Route,
  BrowserRouter as Router,
  Routes,
} from "react-router-dom";

import { SessionProvider } from "./lib/session";
import { AccountPage } from "./routes/Account";
import { LandingPage } from "./routes/Landing";
import { MyChecksPage } from "./routes/MyChecks";
import { PricingPage } from "./routes/Pricing";
import { PrivacyPage } from "./routes/Privacy";
import { ProgressPage } from "./routes/Progress";
import { ReportPage } from "./routes/Report";
import { UploadPage } from "./routes/Upload";

export default function App() {
  return (
    <Router>
      {/*
        로그인 상태를 화면 전체가 같이 본다. **문을 잠그는 장치가 아니다** —
        아래 경로 중 로그인을 요구하는 것은 `/mine` 하나뿐이고, 그것도
        막는 게 아니라 "로그인하시면 여기 남습니다"라고 안내한다 (헌법 4절 단서 1).
      */}
      <SessionProvider>
        <Routes>
          {/*
            **`/` 는 홍보 화면이다.** 검사 앱은 `/check` 로 내려갔다.
            처음 온 사람은 파일이 없고, 이 도구가 무엇인지부터 모른다.
          */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/check" element={<UploadPage />} />
          {/* 남의 회로도를 받는 도구다. 무엇을 저장하는지 말하지 않으면 아무도 안 올린다 */}
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/login" element={<AccountPage mode="login" />} />
          <Route path="/signup" element={<AccountPage mode="signup" />} />
          <Route path="/mine" element={<MyChecksPage />} />
          <Route path="/c/:id" element={<ProgressPage />} />
          <Route path="/r/:id" element={<ReportPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </SessionProvider>
    </Router>
  );
}
