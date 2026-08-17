import type { Finding } from "../types/api";

import { SeverityBadge, TierBadge } from "./Badge";
import { EvidenceBlock } from "./Evidence";

/**
 * 제품의 얼굴.
 *
 * 좌: 회로도가 말하는 것 / 우: 코드·데이터시트가 말하는 것.
 * 가운데 redpen 세로선이 "이 둘이 어긋난다"는 논지 자체다.
 * 근거가 한쪽뿐이어도 이음매는 유지한다 — 비어 있는 쪽이 곧 "아직 모른다"는 뜻이다.
 */
export function FindingCard({ finding }: { finding: Finding }) {
  const left = finding.evidence.filter((e) => e.kind === "netlist");
  const right = finding.evidence.filter((e) => e.kind !== "netlist");
  const unresolved = finding.unresolved_reason !== null;

  return (
    <article className="card">
      <header className="flex flex-wrap items-center gap-2 border-b border-hair px-4 py-3">
        <SeverityBadge severity={finding.severity} />
        <span className="data font-semibold text-ink">{finding.rule}</span>
        {finding.net && <span className="data text-graphite">{finding.net}</span>}
        <span className="ml-auto">
          <TierBadge tier={finding.tier} />
        </span>
      </header>

      <p className="border-b border-hair px-4 py-3 text-[15px] leading-relaxed">{finding.claim}</p>

      {/* 2열 + 이음매. 375px에서는 위아래로 쌓이고 이음매가 가로선이 된다 */}
      <div className="grid grid-cols-1 md:grid-cols-2">
        <section
          className="border-b border-redpen px-4 py-4 md:border-b-0 md:border-r-[1.5px]"
          aria-label="회로도가 말하는 것"
        >
          <p className="label mb-3 text-ink">회로도가 말하는 것</p>
          {left.length > 0 ? (
            <div className="space-y-4">
              {left.map((e, i) => (
                <EvidenceBlock key={i} evidence={e} />
              ))}
            </div>
          ) : (
            <p className="text-[14px] text-graphite">넷리스트 근거 없음</p>
          )}
        </section>

        <section className="px-4 py-4" aria-label="코드가 말하는 것">
          <p className="label mb-3 text-ink">코드가 말하는 것</p>
          {right.length > 0 ? (
            <div className="space-y-4">
              {right.map((e, i) => (
                <EvidenceBlock key={i} evidence={e} />
              ))}
            </div>
          ) : (
            <p className="text-[14px] text-graphite">
              아직 대조하지 못했습니다. 펌웨어와 부품번호가 있어야 이쪽을 채울 수 있습니다.
            </p>
          )}
        </section>
      </div>

      <footer
        className={`border-t px-4 py-3 ${
          unresolved ? "border-amber/40 bg-amber/5" : "border-verify/40 bg-verify/5"
        }`}
      >
        <p className="label mb-1">{unresolved ? "판정 보류 사유" : "해제 근거"}</p>
        {unresolved && <p className="text-[14px] font-medium">{finding.unresolved_reason}</p>}
        {finding.suggestion && (
          <p className="mt-1 text-[14px] leading-relaxed text-ink">{finding.suggestion}</p>
        )}
      </footer>
    </article>
  );
}
