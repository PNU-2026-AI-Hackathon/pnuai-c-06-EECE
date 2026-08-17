import { Link } from "react-router-dom";

/** 상단 바 — 왼쪽 제품명, 오른쪽 메타 칩 */
export function Header({ meta }: { meta?: { label: string; value: string }[] }) {
  return (
    <header className="sticky top-0 z-10 border-b border-line bg-surface/85 backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-y-3 px-5 py-3.5">
        <Link to="/" className="flex items-baseline gap-2">
          <span className="text-[19px] font-extrabold tracking-tight">Prefab</span>
          <span className="text-[13px] text-mute">펌웨어와 회로도 대조 검사</span>
        </Link>

        {meta && meta.length > 0 && (
          // 좁은 화면에서는 메타를 숨긴다. 같은 값이 리포트 본문에 다시 나온다
          <dl className="hidden items-center gap-2 sm:flex">
            {meta.map((m) => (
              <div
                key={m.label}
                className="flex items-baseline gap-1.5 rounded-chip bg-surface-2 px-2.5 py-1.5"
              >
                <dt className="text-[12px] font-semibold text-mute">{m.label}</dt>
                <dd className="data text-[12px] text-sub">{m.value}</dd>
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
      <main className="mx-auto max-w-5xl px-5 py-10">{children}</main>
    </div>
  );
}

/** 섹션 제목 — 번호는 작게 앞에 붙인다 */
export function SectionTitle({ no, children }: { no: string; children: React.ReactNode }) {
  return (
    <h2 className="mb-4 flex items-baseline gap-2">
      <span className="data text-[13px] text-mute">{no}</span>
      <span className="text-[19px] font-bold">{children}</span>
    </h2>
  );
}
