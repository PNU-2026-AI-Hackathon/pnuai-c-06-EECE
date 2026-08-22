import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { LandingPage } from "./routes/Landing";
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
        <Route path="/c/:id" element={<ProgressPage />} />
        <Route path="/r/:id" element={<ReportPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
