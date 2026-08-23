import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { LandingPage } from "./routes/Landing";
import { PricingPage } from "./routes/Pricing";
import { PrivacyPage } from "./routes/Privacy";
import { ProgressPage } from "./routes/Progress";
import { ReportPage } from "./routes/Report";
import { UploadPage } from "./routes/Upload";

export default function App() {
  return (
    <Router>
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
        <Route path="/c/:id" element={<ProgressPage />} />
        <Route path="/r/:id" element={<ReportPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
