import type { Evidence } from "../types/api";

/**
 * 근거 한 덩어리. 넷리스트 · 펌웨어 · 데이터시트 세 종류의 생김새가 다르다.
 * highlight 토큰은 redpen 밑줄로 강조한다 — 어디를 보라는 건지 손가락으로 짚어주는 역할.
 *
 * 어느 소스에서 왔는지는 카드의 레인이 이미 말한다. 여기서는 그 안의 위치만 적는다
 * (파일:줄 · 데이터시트 표/쪽). 같은 말을 두 번 하지 않는다.
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

/** 발췌 — 파일에서 그대로 떠온 것처럼 보여야 한다 */
function Excerpt({ children }: { children: React.ReactNode }) {
  return (
    <pre className="data overflow-x-auto whitespace-pre-wrap break-words border-l-2 border-hair bg-ink/[0.025] py-2 pl-3 pr-2 text-ink">
      {children}
    </pre>
  );
}

function Frame({ label, children }: { label?: string; children: React.ReactNode }) {
  return (
    <div>
      {label && <p className="label mb-1.5">{label}</p>}
      {children}
    </div>
  );
}

export function EvidenceBlock({ evidence }: { evidence: Evidence }) {
  if (evidence.kind === "netlist") {
    return (
      <Frame>
        <Excerpt>{marked(evidence.text, evidence.highlight)}</Excerpt>
      </Frame>
    );
  }

  if (evidence.kind === "firmware") {
    return (
      <Frame label={`${evidence.file} : ${evidence.line}`}>
        <Excerpt>{marked(evidence.snippet, evidence.highlight)}</Excerpt>
      </Frame>
    );
  }

  return (
    <Frame label={evidence.mpn}>
      <Excerpt>{marked(evidence.quote, evidence.highlight)}</Excerpt>
      <p className="mt-1.5 font-cond text-[11px] uppercase tracking-label text-graphite">
        {evidence.table} · p.{evidence.page}
      </p>
    </Frame>
  );
}
