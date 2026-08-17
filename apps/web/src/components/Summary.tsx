import type { CheckInputs, CheckSummary } from "../types/api";

/** 숫자 타일 하나. API가 0을 주면 0으로, null이면 —로 적는다 */
function Tile({ label, value, tone }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="border border-hair bg-vellum-2 px-4 py-3">
      <p className="label">{label}</p>
      <p className={`font-mono text-[28px] font-semibold leading-tight ${tone ?? "text-ink"}`}>
        {value}
      </p>
    </div>
  );
}

export function SummaryTiles({ summary }: { summary: CheckSummary }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <Tile label="치명" value={summary.critical} tone="text-redpen" />
      <Tile label="경고" value={summary.warning} tone="text-amber" />
      <Tile label="해제됨" value={summary.cleared} tone="text-verify" />
      <Tile
        label="실행한 규칙"
        value={`${summary.rules_run}/${summary.rules_run + summary.rules_skipped}`}
      />
    </div>
  );
}

/** 무엇을 받았고 무엇이 없는지. 없는 것을 흐리게 처리하지 않는다 */
export function InputsTable({
  inputs,
  summary,
}: {
  inputs: CheckInputs;
  summary: CheckSummary;
}) {
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
      missing: "없어서 부품을 식별하지 못했습니다. 데이터시트 규칙이 전부 보류됩니다.",
    },
    {
      label: "펌웨어",
      file: inputs.firmware,
      note: inputs.firmware ? "정적 분석 대상" : null,
      missing: "없어서 코드 대조 규칙을 실행하지 못했습니다.",
    },
  ];

  return (
    <ul className="divide-y divide-hair border border-hair">
      {rows.map((r) => (
        <li key={r.label} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-4 py-3">
          <span className="label w-20 shrink-0">{r.label}</span>
          {r.file ? (
            <>
              <span className="data min-w-0 flex-1 break-all text-ink">{r.file.filename}</span>
              {r.note && <span className="data text-graphite">{r.note}</span>}
            </>
          ) : (
            <>
              <span className="data text-graphite">—</span>
              <span className="min-w-0 flex-1 text-[13px] text-amber">{r.missing}</span>
            </>
          )}
        </li>
      ))}
    </ul>
  );
}
