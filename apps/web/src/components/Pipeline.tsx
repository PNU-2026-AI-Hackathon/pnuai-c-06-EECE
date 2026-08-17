import type { PipelineStep } from "../types/api";

import { StepBadge } from "./Badge";

/**
 * 파이프라인 7단계.
 *
 * skipped를 흐리게 하거나 접지 않는다. 사유를 그대로 보여준다.
 * 무엇을 못 했는지 보이는 것이 이 제품의 신뢰다.
 */
export function Pipeline({ steps, running }: { steps: PipelineStep[]; running?: boolean }) {
  return (
    <ol className="card divide-y divide-line overflow-hidden">
      {steps.map((step) => {
        const active = running && step.status === "done";
        return (
          <li
            key={step.step}
            className="relative flex flex-wrap items-center gap-x-3 gap-y-1 px-5 py-4"
          >
            {active && <span aria-hidden className="sweep pointer-events-none absolute inset-0" />}
            <span className="data flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-2 text-[12px] text-sub">
              {step.step}
            </span>
            <span className="min-w-0 flex-1 text-[15px] font-semibold">{step.name}</span>
            <StepBadge status={step.status} />
            {step.detail && <p className="w-full pl-9 text-[13px] text-sub">{step.detail}</p>}
          </li>
        );
      })}
    </ol>
  );
}
