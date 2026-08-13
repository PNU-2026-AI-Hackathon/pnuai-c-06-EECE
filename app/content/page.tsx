import { Megaphone } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { PageHeader } from "@/components/layout/page-header";

/** 홍보 콘텐츠 — 아직 구현 전 (다음 작업 차례) */
export default function ContentPage() {
  return (
    <>
      <PageHeader title="홍보 콘텐츠" description="다음 주 예측을 릴스 대본과 게시글로 옮겨드립니다." />
      <EmptyState
        icon={Megaphone}
        title="준비 중입니다"
        description="예측 결과를 바탕으로 릴스 대본·캡션·해시태그·추천 게시 시각을 만들어 드릴 예정입니다."
      />
    </>
  );
}
