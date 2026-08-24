import type { Severity, StepStatus, Tier, Verdict } from "../types/api";

/**
 * 색만으로 심각도를 구분하지 않는다. 배지 안에 항상 글자가 들어간다.
 * 칩은 옅은 배경 + 진한 글자. 테두리는 쓰지 않는다.
 */

const CHIP = "inline-flex items-center rounded-chip px-2 py-1 text-[12px] font-bold";

const SEVERITY_LABEL: Record<Severity, string> = {
  CRITICAL: "치명",
  WARNING: "경고",
  INFO: "참고",
};

const SEVERITY_STYLE: Record<Severity, string> = {
  CRITICAL: "bg-crit-weak text-crit",
  WARNING: "bg-warn-weak text-warn",
  INFO: "bg-surface-2 text-sub",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`${CHIP} ${SEVERITY_STYLE[severity]}`}>{SEVERITY_LABEL[severity]}</span>;
}

/** 기본 등급인지 차별 등급인지 — 우리 차별점이 어디인지 화면에서 드러낸다 */
export function TierBadge({ tier }: { tier: Tier }) {
  const differentiated = tier === "차별";
  return (
    <span
      className={`${CHIP} ${differentiated ? "bg-ink text-white" : "bg-surface-2 text-mute"}`}
    >
      {tier}
    </span>
  );
}

const VERDICT_LABEL: Record<Verdict, string> = {
  FAIL: "어긋남",
  PASS: "해제됨",
  UNRESOLVED: "확인 필요",
};

const VERDICT_STYLE: Record<Verdict, string> = {
  FAIL: "bg-surface-2 text-ink",
  PASS: "bg-ok-weak text-ok",
  UNRESOLVED: "bg-warn-weak text-warn",
};

/** 심각도와 별개로 "판정을 내렸는가"를 따로 말한다. 확인 필요를 실패처럼 보이게 하지 않는다 */
export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return <span className={`${CHIP} ${VERDICT_STYLE[verdict]}`}>{VERDICT_LABEL[verdict]}</span>;
}

const STEP_LABEL: Record<StepStatus, string> = {
  done: "완료",
  partial: "일부",
  skipped: "건너뜀",
  failed: "실패",
};

const STEP_STYLE: Record<StepStatus, string> = {
  done: "bg-ok-weak text-ok",
  partial: "bg-warn-weak text-warn",
  skipped: "bg-warn-weak text-warn",
  failed: "bg-crit-weak text-crit",
};

export function StepBadge({ status }: { status: StepStatus }) {
  return <span className={`${CHIP} ${STEP_STYLE[status]}`}>{STEP_LABEL[status]}</span>;
}
