import { Settings2 } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { PageHeader } from "@/components/layout/page-header";

/** 설정 — 아직 구현 전 (매장 정보와 CSV 업로드가 들어갈 자리) */
export default function SettingsPage() {
  return (
    <>
      <PageHeader title="설정" description="매장 정보와 올린 매출 파일을 관리합니다." />
      <EmptyState
        icon={Settings2}
        title="준비 중입니다"
        description="매장 정보 수정과 CSV 업로드·정규화 확인 화면이 들어갈 자리입니다."
      />
    </>
  );
}
