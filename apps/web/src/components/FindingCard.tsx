import type { CheckInputs, EvidenceKind, Finding } from "../types/api";

import { SeverityBadge, TierBadge, VerdictBadge } from "./Badge";
import { EvidenceBlock } from "./Evidence";
import { SourceMark, SourceRail, type SourceState } from "./Mark";

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

const LANES: {
  kind: EvidenceKind;
  label: string;
  /** 소스 자체가 없을 때 — 무엇을 주면 채워지는지 */
  unknown: string;
  /** 소스는 받았지만 이 판정의 근거로 쓰이지 않았을 때 */
  none: string;
}[] = [
  {
    kind: "netlist",
    label: "회로도가 아는 것",
    unknown: "넷리스트가 없어 회로 연결을 확인하지 못했습니다.",
    none: "이 판정은 회로도 연결을 근거로 쓰지 않았습니다.",
  },
  {
    kind: "firmware",
    label: "코드가 아는 것",
    unknown: "펌웨어를 올리면 이 줄이 채워집니다. 지금은 코드가 이 핀을 어떻게 쓰는지 모릅니다.",
    none: "펌웨어는 읽었지만, 이 판정은 코드를 근거로 쓰지 않았습니다.",
  },
  {
    kind: "datasheet",
    label: "데이터시트가 아는 것",
    unknown: "부품 목록(BOM)을 올리면 데이터시트를 찾아 이 줄을 채웁니다.",
    none: "데이터시트에서 이 판정에 쓸 값을 찾지 못했습니다.",
  },
];

/** 소스를 갖고 있는지 — 근거가 붙었는지와 별개다 */
function haveSource(kind: EvidenceKind, inputs?: CheckInputs): boolean {
  if (!inputs) return false;
  if (kind === "netlist") return inputs.netlist !== null;
  if (kind === "firmware") return inputs.firmware !== null;
  return inputs.bom !== null; // 데이터시트는 BOM의 부품번호로 찾는다
}

const STATE_LABEL: Record<SourceState, string> = {
  read: "읽음",
  none: "근거 없음",
  unknown: "모름",
};

function Lane({
  label,
  state,
  blank,
  seam,
  children,
}: {
  label: string;
  state: SourceState;
  /** 근거가 없을 때 쓸 문구 */
  blank: string;
  /** 회로도 레인과 코드 레인 사이의 이음매 */
  seam?: boolean;
  children?: React.ReactNode;
}) {
  const read = state === "read";
  return (
    <section
      aria-label={label}
      className={`grid grid-cols-[12px_1fr] gap-x-3.5 px-5 md:grid-cols-[12px_10rem_1fr] md:gap-x-5 ${
        read ? "py-5" : "py-4"
      } ${seam ? "border-t-[1.5px] border-crit/45" : ""}`}
    >
      {/* 레일 — 구리(실선)와 틈(점선) */}
      <div aria-hidden className="relative col-start-1 row-span-2 md:row-span-1">
        <SourceRail state={state} />
        <span className="absolute left-0 top-1.5 block">
          <SourceMark state={state} />
        </span>
      </div>

      {/* 소스 이름 — 좁은 화면에서는 내용 위에, 넓은 화면에서는 왼쪽 열에 */}
      <p
        className={`col-start-2 row-start-1 flex flex-wrap items-baseline gap-x-2 md:flex-col md:gap-y-0.5 ${
          read ? "mb-2 md:mb-0" : "mb-1 md:mb-0"
        }`}
      >
        <span className="text-[13px] font-bold text-ink">{label}</span>
        <span
          className={`text-[12px] font-semibold ${
            state === "unknown" ? "text-warn" : "text-mute"
          }`}
        >
          {STATE_LABEL[state]}
        </span>
      </p>

      <div className="col-start-2 row-start-2 min-w-0 md:col-start-3 md:row-start-1">
        {read ? (
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

export function FindingCard({
  finding,
  inputs,
}: {
  finding: Finding;
  /** 무엇을 제출받았는지. "모름"과 "근거 없음"을 구분하는 데 쓴다 */
  inputs?: CheckInputs;
}) {
  const unresolved = finding.unresolved_reason !== null;
  const foot: Foot = unresolved ? "unresolved" : finding.verdict === "PASS" ? "cleared" : "next";

  return (
    <article className="card overflow-hidden">
      <header className="border-b border-line px-5 py-4">
        {/*
          **발견 제목은 heading 이다.**

          `span` 이면 스크린리더가 발견 사이를 넘어갈 수 없다 — 리포트에 h3 가 하나도
          없어서 발견 여러 건이 h2 아래 평평하게 깔려 있었다. 규칙 ID(`R07`)는 제목이
          아니라 식별자라 heading 밖에 둔다.
        */}
        <div className="flex items-baseline gap-2">
          <SeverityBadge severity={finding.severity} />
          <span className="data font-semibold text-sub">{finding.rule}</span>
          <h3 className="min-w-0 text-[17px] font-bold tracking-tight">{finding.title}</h3>
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
        const state: SourceState =
          items.length > 0 ? "read" : haveSource(lane.kind, inputs) ? "none" : "unknown";
        return (
          <Lane
            key={lane.kind}
            label={lane.label}
            state={state}
            blank={state === "none" ? lane.none : lane.unknown}
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
