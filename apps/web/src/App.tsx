import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { ProgressPage } from "./routes/Progress";
import { ReportPage } from "./routes/Report";
import { UploadPage } from "./routes/Upload";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/c/:id" element={<ProgressPage />} />
        <Route path="/r/:id" element={<ReportPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
