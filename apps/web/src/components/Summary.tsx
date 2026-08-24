import type { CheckInputs, CheckSummary } from "../types/api";

import { SourceMark } from "./Mark";

/**
 * 숫자 타일 하나. API가 0을 주면 0으로, null이면 —로 적는다.
 *
 * `hint` 는 라벨 아래 작은 글씨다. **「해제됨」이 이 제품에만 있는 말**이라
 * 처음 보는 사람은 무슨 뜻인지 모른다 — 숫자만 크게 보여 주고 뜻을 안 말하면
 * 요약이 아니라 암호가 된다.
 */
function Tile({
  label,
  value,
  tone,
  hint,
}: {
  label: string;
  value: number | string;
  tone?: string;
  hint?: string;
}) {
  return (
    <div className="card px-5 py-4">
      <p className="label">{label}</p>
      <p className={`mt-1 text-[30px] font-extrabold tracking-tight ${tone ?? "text-ink"}`}>
        {value}
      </p>
      {hint && <p className="mt-1 text-[12px] leading-snug text-mute">{hint}</p>}
    </div>
  );
}

export function SummaryTiles({ summary }: { summary: CheckSummary }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <Tile label="치명" value={summary.critical} tone="text-crit" />
      <Tile label="경고" value={summary.warning} tone="text-warn" />
      {/* 정보는 결함이 아니다. 0 이면 타일을 만들지 않는다 — 빈 칸이 늘면 요약이 흐려진다 */}
      {summary.info > 0 && <Tile label="정보" value={summary.info} tone="text-sub" />}
      <Tile
        label="해제됨"
        value={summary.cleared}
        tone="text-ok"
        hint="경고였다가 데이터시트로 안전이 확인된 항목"
      />
      <Tile
        label="실행한 규칙"
        value={`${summary.rules_run}/${summary.rules_total}`}
        hint={
          summary.rules_skipped > 0
            ? `${summary.rules_skipped}개는 돌리지 못했습니다`
            : "전부 돌렸습니다"
        }
      />
    </div>
  );
}

/** 무엇을 받았고 무엇이 없는지. 없는 것을 흐리게 처리하지 않는다 */
export function InputsTable({ inputs, summary }: { inputs: CheckInputs; summary: CheckSummary }) {
  const rows = [
    {
      label: "넷리스트",
      file: inputs.netlist,
      note: inputs.netlist ? `네트 ${inputs.netlist.nets} · 부품 ${inputs.netlist.parts}` : null,
      missing: "필수 입력입니다.",
    },
    {
      label: "부품 목록",
      file: inputs.bom,
      note: inputs.bom ? `부품 식별 ${summary.parts_identified}/${summary.parts_total}` : null,
      missing: "없어서 부품을 알아보지 못했습니다. 데이터시트로 확인하는 규칙이 「확인 필요」로 남습니다.",
    },
    {
      label: "펌웨어",
      file: inputs.firmware,
      // 서버가 파일 수를 주면 그걸 쓴다. 안 주면 개수를 말하지 않는다
      note: inputs.firmware
        ? inputs.firmware.files != null
          ? `파일 ${inputs.firmware.files}개`
          : "정적 분석 대상"
        : null,
      missing: "없어서 코드 대조 규칙을 실행하지 못했습니다.",
    },
  ];

  return (
    <ul className="card divide-y divide-line overflow-hidden">
      {rows.map((r) => (
        <li key={r.label} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-5 py-4">
          <SourceMark state={r.file !== null ? "read" : "unknown"} />
          <span className="w-20 shrink-0 text-[14px] font-bold">{r.label}</span>
          {r.file ? (
            <>
              <span className="data min-w-0 flex-1 break-all text-sub">{r.file.filename}</span>
              {r.note && <span className="data text-mute">{r.note}</span>}
            </>
          ) : (
            <>
              <span className="data text-mute">—</span>
              <span className="min-w-0 flex-1 text-[14px] text-warn">{r.missing}</span>
            </>
          )}
        </li>
      ))}
    </ul>
  );
}
