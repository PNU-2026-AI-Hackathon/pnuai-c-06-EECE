import type { Candidate, Discovery as DiscoveryData } from "../types/api";

/**
 * 규칙 후보 — **발견이 아니다.**
 *
 * 화면에서 발견처럼 보이면 안 된다. 그래서 세 가지를 다르게 한다 —
 * 제목이 「후보」이고, 심각도 배지가 없고, 배경이 표면(surface)이 아니라 바탕(bg)이다.
 * 발견 카드는 흰 카드로 떠 있고 이것은 바탕에 가라앉아 있다.
 *
 * 이 섹션이 존재하는 이유는 `_docs/규모_실험.md` 에 있다 — 같은 케이스를 LLM 에
 * 던졌더니 우리 규칙 12개가 못 본 **진짜 결함**을 찾아냈고 그게 R14 가 됐다.
 * 그때 사람이 손으로 한 일을 제품이 한다.
 */
export function Discovery({ data }: { data: DiscoveryData }) {
  if (data.unavailable) {
    return (
      <p className="rounded-block bg-surface-2 px-4 py-3.5 text-[14px] leading-relaxed text-sub">
        <strong className="font-bold text-ink">물어보지 못했습니다.</strong> {data.unavailable}
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <p className="rounded-block bg-surface-2 px-4 py-3.5 text-[14px] leading-relaxed text-sub">
        <strong className="font-bold text-ink">아래는 판정이 아니라 제안입니다.</strong> 지금
        규칙이 보지 않는 자리를 모델이 짚은 것이고,{" "}
        <strong className="font-bold text-ink">근거가 실제로 그 자리에 있는지 코드가 확인한</strong>{" "}
        것만 남겼습니다. 채택할지는 사람이 정합니다.
      </p>

      {data.candidates.length === 0 && (
        <p className="card px-5 py-8 text-center text-[15px] text-sub">
          새로 올릴 후보가 없습니다.
        </p>
      )}

      {data.candidates.map((c, i) => (
        <CandidateCard key={`${c.title}-${i}`} candidate={c} />
      ))}

      {/* **버린 것을 숨기지 않는다.** 몇 개를 왜 버렸는지 보여야 남은 것을 믿을 수 있다 */}
      {data.dropped.length > 0 && (
        <details className="rounded-block border border-line bg-surface-2/60 px-4 py-3">
          <summary className="cursor-pointer text-[13px] font-bold text-sub">
            코드가 거른 것 {data.dropped.length}건
          </summary>
          <ul className="mt-3 space-y-2">
            {data.dropped.map((d, i) => (
              <li key={i} className="text-[13px] leading-relaxed text-mute">
                <span className="font-semibold text-sub">{d.title}</span>
                <br />
                {d.reason}
              </li>
            ))}
          </ul>
        </details>
      )}

      {data.notes.map((n) => (
        <p key={n} className="text-[13px] text-mute">
          {n}
        </p>
      ))}
    </div>
  );
}

function CandidateCard({ candidate }: { candidate: Candidate }) {
  return (
    <article className="rounded-card border border-dashed border-line bg-surface/70 px-5 py-4">
      <div className="mb-2 flex items-baseline gap-2">
        <span className="rounded-chip bg-surface-2 px-2 py-0.5 text-[11px] font-bold text-sub">
          후보
        </span>
        <h3 className="min-w-0 text-[16px] font-bold tracking-tight">{candidate.title}</h3>
      </div>

      <p className="mb-3 text-[14px] leading-relaxed text-sub">{candidate.why}</p>

      <dl className="space-y-1.5">
        {candidate.citations.map((c, i) => (
          <div key={i} className="rounded-block bg-surface-2 px-3 py-2">
            <dt className="label mb-0.5">
              {c.kind === "firmware" ? "코드" : "회로도"} · {c.where}
              {c.what ? `:${c.what}` : ""}
            </dt>
            {c.quote && <dd className="data whitespace-pre-wrap text-sub">{c.quote}</dd>}
          </div>
        ))}
      </dl>
    </article>
  );
}
