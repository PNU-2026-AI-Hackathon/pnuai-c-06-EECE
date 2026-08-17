import type { Severity, StepStatus, Tier } from "../types/api";

/**
 * 색만으로 심각도를 구분하지 않는다. 배지 안에 항상 글자가 들어간다.
 */

const SEVERITY_LABEL: Record<Severity, string> = {
  CRITICAL: "치명",
  WARNING: "경고",
  INFO: "참고",
};

const SEVERITY_STYLE: Record<Severity, string> = {
  CRITICAL: "border-redpen text-redpen",
  WARNING: "border-amber text-amber",
  INFO: "border-graphite text-graphite",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`border px-1.5 py-0.5 font-cond text-[11px] font-semibold uppercase tracking-label ${SEVERITY_STYLE[severity]}`}
    >
      {SEVERITY_LABEL[severity]}
    </span>
  );
}

/** 기본 등급인지 차별 등급인지 — 우리 차별점이 어디인지 화면에서 드러낸다 */
export function TierBadge({ tier }: { tier: Tier }) {
  const differentiated = tier === "차별";
  return (
    <span
      className={`border px-1.5 py-0.5 font-cond text-[11px] font-semibold uppercase tracking-label ${
        differentiated ? "border-ink bg-ink text-vellum" : "border-hair text-graphite"
      }`}
    >
      {tier}
    </span>
  );
}

const STEP_LABEL: Record<StepStatus, string> = {
  done: "완료",
  partial: "일부",
  skipped: "건너뜀",
  failed: "실패",
};

const STEP_STYLE: Record<StepStatus, string> = {
  done: "border-verify text-verify",
  partial: "border-amber text-amber",
  skipped: "border-amber text-amber",
  failed: "border-redpen text-redpen",
};

export function StepBadge({ status }: { status: StepStatus }) {
  return (
    <span
      className={`border px-1.5 py-0.5 font-cond text-[11px] font-semibold uppercase tracking-label ${STEP_STYLE[status]}`}
    >
      {STEP_LABEL[status]}
    </span>
  );
}
