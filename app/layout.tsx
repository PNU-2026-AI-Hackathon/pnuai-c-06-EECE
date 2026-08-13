import type { Metadata, Viewport } from "next";

import { Sidebar } from "@/components/layout/sidebar";

import "./globals.css";

export const metadata: Metadata = {
  title: "STAFFI | 대학상권 AI 매장 직원",
  description: "부산대학교 학사일정과 매장 데이터를 분석해, 다음에 무엇이 달라질지와 지금 무엇을 해야 하는지 알려드립니다.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // 확대를 막지 않는다 — 시력이 낮은 사용자를 배려
  maximumScale: 5,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-background text-foreground">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
        >
          본문으로 건너뛰기
        </a>

        <div className="flex min-h-screen">
          <Sidebar />
          <main id="main" className="min-w-0 flex-1 pb-20 lg:pb-0">
            <div className="mx-auto max-w-5xl space-y-8 px-5 py-8 lg:px-10 lg:py-12">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
