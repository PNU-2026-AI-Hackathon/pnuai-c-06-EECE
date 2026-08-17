import type { Evidence } from "../types/api";

/**
 * 근거 한 덩어리. 넷리스트 · 펌웨어 · 데이터시트 세 종류의 생김새가 다르다.
 * highlight 토큰은 redpen 밑줄로 강조한다 — 어디를 보라는 건지 손가락으로 짚어주는 역할.
 */

/** 텍스트에서 highlight 토큰을 찾아 밑줄 친 조각들로 쪼갠다 */
function marked(text: string, tokens: string[] | undefined) {
  if (!tokens || tokens.length === 0) return text;

  // 정규식 특수문자를 escape 하고 긴 토큰부터 매칭한다 (짧은 게 먼저 먹지 않도록)
  const escaped = [...tokens]
    .sort((a, b) => b.length - a.length)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const parts = text.split(new RegExp(`(${escaped.join("|")})`, "g"));

  return parts.map((part, i) =>
    tokens.includes(part) ? (
      <mark
        key={i}
        className="bg-redpen/10 text-redpen underline decoration-redpen decoration-1 underline-offset-2"
      >
        {part}
      </mark>
    ) : (
      part
    )
  );
}

function Frame({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="label mb-1.5">{label}</p>
      {children}
    </div>
  );
}

export function EvidenceBlock({ evidence }: { evidence: Evidence }) {
  if (evidence.kind === "netlist") {
    return (
      <Frame label="넷리스트">
        <pre className="data whitespace-pre-wrap break-words text-ink">
          {marked(evidence.text, evidence.highlight)}
        </pre>
      </Frame>
    );
  }

  if (evidence.kind === "firmware") {
    return (
      <Frame label={`${evidence.file} : ${evidence.line}`}>
        <pre className="data whitespace-pre-wrap break-words text-ink">
          {marked(evidence.snippet, evidence.highlight)}
        </pre>
      </Frame>
    );
  }

  return (
    <Frame label={`데이터시트 · ${evidence.mpn}`}>
      <blockquote className="data border-l-2 border-hair pl-3 text-ink">
        {marked(evidence.quote, evidence.highlight)}
      </blockquote>
      <p className="mt-1.5 font-cond text-[11px] uppercase tracking-label text-graphite">
        {evidence.table} · p.{evidence.page}
      </p>
    </Frame>
  );
}
