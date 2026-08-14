"use client";

import { useState } from "react";
import { AlertTriangle, Check, ChevronDown, X } from "lucide-react";

import type { AgentAction, Recommendation, RecommendationPriority } from "@/types";

import { DataOriginBadge } from "@/components/common/mock-data-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { confidenceLabel, formatDateShort, formatWon } from "@/lib/format";
import { cn } from "@/lib/utils";

/** 우선순위 — 색과 함께 라벨·아이콘으로도 구분한다 */
const PRIORITY: Record<
  RecommendationPriority,
  { label: string; className: string; icon: boolean }
> = {
  high: { label: "먼저 하세요", className: "bg-down text-primary-foreground", icon: true },
  medium: { label: "확인해 보세요", className: "bg-secondary text-secondary-foreground", icon: false },
  low: { label: "참고", className: "bg-muted text-muted-foreground", icon: false },
};

const DECLINE_REASONS = [
  { code: "already_doing", label: "이미 하고 있어요" },
  { code: "not_applicable", label: "우리 가게엔 안 맞아요" },
  { code: "no_time", label: "할 시간이 없어요" },
  { code: "disagree_with_data", label: "숫자가 안 맞는 것 같아요" },
];

/**
 * 행동 추천 한 건.
 * 사장님의 승인/거절이 다음 추천을 고치는 학습 신호가 되므로, 거절 사유까지 받는다.
 */
export function RecommendationCard({
  recommendation,
  action,
  defaultOpen = false,
}: {
  recommendation: Recommendation;
  /** 승인 시 STAFFI가 대신 할 수 있는 행동 */
  action?: AgentAction;
  /** 근거를 처음부터 펼쳐둘지 */
  defaultOpen?: boolean;
}) {
  const r = recommendation;
  const [status, setStatus] = useState(r.status);
  const [showEvidence, setShowEvidence] = useState(defaultOpen);
  const [showReasons, setShowReasons] = useState(false);
  const [declineReason, setDeclineReason] = useState<string | null>(null);
  // 승인은 실행과 별개다 — 승인 없이 실행하지 않는다는 규칙을 화면에서도 지킨다
  const [approved, setApproved] = useState(action?.status === "approved" || action?.status === "executed");
  const priority = PRIORITY[r.priority];

  return (
    <Card className="shadow-none">
      <CardContent className="space-y-4 p-6">
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={cn("gap-1.5 text-base font-semibold hover:opacity-100", priority.className)}>
            {priority.icon && <AlertTriangle aria-hidden className="size-4" />}
            {priority.label}
          </Badge>
          <Badge variant="outline" className="text-base font-medium">
            {confidenceLabel(r.confidenceLevel)}
          </Badge>
          <span className="text-base text-muted-foreground">
            {formatDateShort(r.actionWindow.start)}까지
          </span>
          <DataOriginBadge origin={r.origin} />
        </div>

        <div className="space-y-2">
          <h3 className="text-2xl font-bold leading-snug">{r.action}</h3>
          <p className="text-base leading-relaxed text-foreground/90">{r.description}</p>
          {r.estimatedImpact !== null && (
            <p className="text-base">
              <span className="font-semibold">예상 효과: </span>약 {formatWon(r.estimatedImpact)}
              <span className="text-muted-foreground"> (실제 결과와 다를 수 있습니다)</span>
            </p>
          )}
        </div>

        <div>
          <button
            type="button"
            onClick={() => setShowEvidence((v) => !v)}
            className="flex items-center gap-1.5 rounded-md text-base font-semibold text-primary underline-offset-4 hover:underline"
            aria-expanded={showEvidence}
          >
            왜 이렇게 봤는지 {showEvidence ? "접기" : `보기 (${r.evidence.length}건)`}
            <ChevronDown aria-hidden className={cn("size-4 transition-transform", showEvidence && "rotate-180")} />
          </button>

          {showEvidence && (
            <ul className="mt-3 space-y-3 border-l-2 pl-4">
              {r.evidence.map((e) => (
                <li key={e.statement}>
                  <p className="text-base font-medium leading-snug">{e.statement}</p>
                  <p className="text-sm text-muted-foreground">근거: {e.source}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        {status === "proposed" ? (
          <div className="space-y-3 border-t pt-4">
            <div className="flex flex-wrap gap-3">
              <Button size="lg" onClick={() => setStatus("accepted")}>
                <Check aria-hidden className="mr-2 size-5" />
                하겠습니다
              </Button>
              <Button size="lg" variant="outline" onClick={() => setShowReasons((v) => !v)}>
                <X aria-hidden className="mr-2 size-5" />
                안 할래요
              </Button>
            </div>

            {showReasons && (
              <div className="space-y-2">
                <p className="text-base font-medium">이유를 알려주시면 다음 추천이 나아집니다</p>
                <div className="flex flex-wrap gap-2">
                  {DECLINE_REASONS.map((reason) => (
                    <Button
                      key={reason.code}
                      size="lg"
                      variant="secondary"
                      onClick={() => {
                        setDeclineReason(reason.label);
                        setStatus("declined");
                        setShowReasons(false);
                      }}
                    >
                      {reason.label}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-3 border-t pt-4">
            <p className="text-base font-semibold">
              {status === "accepted" ? "하기로 하셨습니다" : `안 하기로 하셨습니다${declineReason ? ` — ${declineReason}` : ""}`}
            </p>
            <Button
              size="lg"
              variant="ghost"
              onClick={() => {
                setStatus("proposed");
                setApproved(false);
                setDeclineReason(null);
              }}
            >
              되돌리기
            </Button>
          </div>
        )}

        {status === "accepted" && action && (
          <div className="rounded-lg border bg-secondary/60 p-4">
            <p className="text-base font-semibold">STAFFI가 대신 할 수 있는 일</p>
            <p className="mt-1 text-base">{action.title}</p>
            {action.preview && (
              <p className="mt-3 whitespace-pre-line rounded-md bg-card p-3 text-base leading-relaxed">
                {action.preview}
              </p>
            )}

            {approved ? (
              <div className="mt-3 space-y-1">
                <p className="flex items-center gap-1.5 text-base font-semibold text-up">
                  <Check aria-hidden className="size-5" />
                  승인하셨습니다
                </p>
                <p className="text-sm text-muted-foreground">
                  {action.executeBy
                    ? `${formatDateShort(action.executeBy)}에 실행할 일로 적어 두었습니다.`
                    : "실행할 일로 적어 두었습니다."}{" "}
                  실제 게시·발주 연동은 아직 준비 중이라, 지금은 승인 기록만 남습니다.
                </p>
                <Button
                  size="lg"
                  variant="ghost"
                  className="mt-1"
                  onClick={() => setApproved(false)}
                >
                  승인 취소
                </Button>
              </div>
            ) : (
              <>
                <p className="mt-3 text-sm text-muted-foreground">
                  사장님이 확인하고 승인하기 전에는 게시하지 않습니다.
                </p>
                <Button size="lg" className="mt-3" onClick={() => setApproved(true)}>
                  <Check aria-hidden className="mr-2 size-5" />
                  확인하고 승인하기
                </Button>
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
