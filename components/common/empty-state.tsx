import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

import { cn } from "@/lib/utils";

/** 데이터가 없을 때의 안내. 빈 화면을 그냥 두지 않고 다음 행동을 알려준다 */
export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: {
  /** 상단 아이콘 */
  icon?: LucideIcon;
  /** 한 줄 제목 (예: "아직 올린 매출 파일이 없습니다") */
  title: string;
  /** 무엇을 하면 되는지 설명 */
  description?: string;
  /** 버튼 등 다음 행동 */
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed bg-card px-6 py-14 text-center",
        className
      )}
    >
      <div className="mb-4 flex size-14 items-center justify-center rounded-full bg-secondary">
        <Icon aria-hidden className="size-7 text-muted-foreground" />
      </div>
      <h3 className="text-xl font-bold">{title}</h3>
      {description && <p className="mt-2 max-w-md text-base text-muted-foreground">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
