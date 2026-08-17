import type { EvidenceKind, Finding } from "../types/api";

import { SeverityBadge, TierBadge, VerdictBadge } from "./Badge";
import { EvidenceBlock } from "./Evidence";
import { SourceMark, SourceRail } from "./Mark";

/**
 * 제품의 얼굴.
 *
 * 소스마다 한 줄(레인)을 준다 — 회로도 / 코드 / 데이터시트.
 * 세로축은 "누가 말했는가" 하나만 뜻한다. 가로축에 다른 의미를 겹치지 않는다.
 *
 * 왼쪽 세로 레일이 소스의 상태다.
 *   실선 + 채운 마디 = 우리가 읽은 사실
 *   점선 + 빈 마디   = 아직 모르는 것 (입력이 없거나 못 읽었다)
 * 레인은 근거가 없어도 지우지 않는다. 빈 레인이 곧 "무엇이 있어야 판정이 되는가"다.
 *
 * 회로도 레인과 나머지 사이의 1.5px 빨간 가로선이 이음매다 —
 * 회로도가 말하는 것과 코드가 말하는 것이 갈라지는 자리.
 */

const LANES: { kind: EvidenceKind; label: string; blank: string }[] = [
  {
    kind: "netlist",
    label: "회로도가 아는 것",
    blank: "이 발견에는 넷리스트 근거가 없습니다.",
  },
  {
    kind: "firmware",
    label: "코드가 아는 것",
    blank: "펌웨어를 올리면 이 줄이 채워집니다. 지금은 코드가 이 핀을 어떻게 쓰는지 모릅니다.",
  },
  {
    kind: "datasheet",
    label: "데이터시트가 아는 것",
    blank: "부품 목록(BOM)을 올리면 데이터시트를 찾아 이 줄을 채웁니다.",
  },
];

function Lane({
  label,
  known,
  blank,
  seam,
  children,
}: {
  label: string;
  known: boolean;
  blank: string;
  /** 회로도 레인과 코드 레인 사이의 이음매 */
  seam?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <section
      aria-label={label}
      className={`grid grid-cols-[12px_1fr] gap-x-3.5 px-5 md:grid-cols-[12px_10rem_1fr] md:gap-x-5 ${
        known ? "py-5" : "py-4"
      } ${seam ? "border-t-[1.5px] border-crit/45" : ""}`}
    >
      {/* 레일 — 구리(실선)와 틈(점선) */}
      <div aria-hidden className="relative col-start-1 row-span-2 md:row-span-1">
        <SourceRail known={known} />
        <span className="absolute left-0 top-1.5 block">
          <SourceMark known={known} />
        </span>
      </div>

      {/* 소스 이름 — 좁은 화면에서는 내용 위에, 넓은 화면에서는 왼쪽 열에 */}
      <p
        className={`col-start-2 row-start-1 flex flex-wrap items-baseline gap-x-2 md:flex-col md:gap-y-0.5 ${
          known ? "mb-2 md:mb-0" : "mb-1 md:mb-0"
        }`}
      >
        <span className="text-[13px] font-bold text-ink">{label}</span>
        <span className={`text-[12px] font-semibold ${known ? "text-mute" : "text-warn"}`}>
          {known ? "읽음" : "모름"}
        </span>
      </p>

      <div className="col-start-2 row-start-2 min-w-0 md:col-start-3 md:row-start-1">
        {known ? (
          <div className="space-y-4">{children}</div>
        ) : (
          <p className="text-[14px] leading-relaxed text-sub">{blank}</p>
        )}
      </div>
    </section>
  );
}

/** 카드 아래쪽은 셋 중 하나다 — 왜 판정을 못 했는가 / 왜 해제됐는가 / 이제 무엇을 하는가 */
type Foot = "unresolved" | "cleared" | "next";

const FOOTER_LABEL: Record<Foot, string> = {
  unresolved: "판정 보류 사유",
  cleared: "해제 근거",
  next: "다음 단계",
};

const FOOTER_TONE: Record<Foot, string> = {
  unresolved: "bg-warn-weak",
  cleared: "bg-ok-weak",
  next: "bg-surface-2",
};

const FOOTER_LABEL_TONE: Record<Foot, string> = {
  unresolved: "text-warn",
  cleared: "text-ok",
  next: "text-mute",
};

export function FindingCard({ finding }: { finding: Finding }) {
  const unresolved = finding.unresolved_reason !== null;
  const foot: Foot = unresolved ? "unresolved" : finding.verdict === "PASS" ? "cleared" : "next";

  return (
    <article className="card overflow-hidden">
      <header className="border-b border-line px-5 py-4">
        <div className="flex items-baseline gap-2">
          <SeverityBadge severity={finding.severity} />
          <span className="data font-semibold text-sub">{finding.rule}</span>
          <span className="min-w-0 text-[17px] font-bold tracking-tight">{finding.title}</span>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {finding.net && (
            <span className="data min-w-0 break-all text-mute">{finding.net}</span>
          )}
          <span className="ml-auto flex shrink-0 gap-2">
            <TierBadge tier={finding.tier} />
            <VerdictBadge verdict={finding.verdict} />
          </span>
        </div>
      </header>

      <p className="border-b border-line px-5 py-4 text-[15px] leading-relaxed text-sub">
        {finding.claim}
      </p>

      {LANES.map((lane, i) => {
        const items = finding.evidence.filter((e) => e.kind === lane.kind);
        return (
          <Lane
            key={lane.kind}
            label={lane.label}
            known={items.length > 0}
            blank={lane.blank}
            seam={i === 1}
          >
            {items.map((e, j) => (
              <EvidenceBlock key={j} evidence={e} />
            ))}
          </Lane>
        );
      })}

      {/* 할 말이 없으면 빈 칸을 만들지 않는다 */}
      {(unresolved || finding.suggestion) && (
        <footer className={`border-t border-line px-5 py-4 ${FOOTER_TONE[foot]}`}>
          <p className={`mb-1.5 text-[12px] font-bold ${FOOTER_LABEL_TONE[foot]}`}>
            {FOOTER_LABEL[foot]}
          </p>
          {unresolved && (
            <p className="text-[15px] font-bold text-ink">{finding.unresolved_reason}</p>
          )}
          {finding.suggestion && (
            <p className="mt-1 text-[14px] leading-relaxed text-sub">{finding.suggestion}</p>
          )}
        </footer>
      )}
    </article>
  );
}
