import type { ReactNode } from "react";

import { MockDataBadge } from "@/components/common/mock-data-badge";

/** 각 화면 상단의 제목 영역. 화면마다 같은 위치·같은 크기로 유지한다 */
export function PageHeader({
  title,
  description,
  isMockData = false,
  action,
}: {
  /** 화면 제목 */
  title: string;
  /** 한 줄 설명 — 사장님이 이 화면을 왜 보는지 */
  description?: string;
  /** 화면 전체가 예시 데이터인 경우 */
  isMockData?: boolean;
  /** 우측 버튼 등 */
  action?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
          {isMockData && <MockDataBadge size="lg" />}
        </div>
        {description && <p className="text-lg text-muted-foreground">{description}</p>}
      </div>
      {action}
    </header>
  );
}
