import { Link } from "react-router-dom";

/** 도면 표제란 — 좌측 제품명, 우측 메타 3칸 */
export function Header({ meta }: { meta?: { label: string; value: string }[] }) {
  return (
    <header className="border-b border-hair bg-vellum-2">
      <div className="mx-auto flex max-w-5xl flex-wrap items-stretch justify-between gap-y-3 px-4 py-3">
        <Link to="/" className="flex flex-col justify-center">
          <span className="font-cond text-lg font-semibold uppercase tracking-label">Prefab</span>
          <span className="text-[12px] text-graphite">펌웨어와 회로도 대조 검사</span>
        </Link>

        {meta && meta.length > 0 && (
          <dl className="grid grid-cols-3 divide-x divide-hair border border-hair">
            {meta.map((m) => (
              <div key={m.label} className="px-3 py-1.5">
                <dt className="label">{m.label}</dt>
                <dd className="data text-ink">{m.value}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </header>
  );
}

export function Page({
  meta,
  children,
}: {
  meta?: { label: string; value: string }[];
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen">
      <Header meta={meta} />
      <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
    </div>
  );
}

/** 섹션 제목 — 번호를 붙여 도면 항목처럼 */
export function SectionTitle({ no, children }: { no: string; children: React.ReactNode }) {
  return (
    <h2 className="mb-3 flex items-baseline gap-2 border-b border-hair pb-2">
      <span className="data text-graphite">{no}</span>
      <span className="font-cond text-base font-semibold uppercase tracking-label">{children}</span>
    </h2>
  );
}
