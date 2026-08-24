import { Link } from "react-router-dom";

import { useSession } from "../lib/session";

/** 상단 바 — 왼쪽 제품명, 오른쪽 메타 칩 */
export function Header({
  meta,
}: {
  meta?: { label: string; value: string }[];
}) {
  return (
    // `no-print` — 종이에는 고정 상단 바가 뜻이 없다. **클래스로 직접 표시한다** —
    // 선택자로 `header` 를 통째로 잡으면 발견 카드의 머리까지 지워진다 (그것도 `<header>` 다)
    <header className="no-print sticky top-0 z-10 border-b border-line bg-surface/85 backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-y-3 px-5 py-3.5">
        <Link
          to="/"
          className="-mx-2 flex min-h-[44px] items-center gap-2 rounded-block px-2"
        >
          <span className="text-[19px] font-extrabold tracking-tight">
            Prefab
          </span>
          <span className="text-[13px] text-mute">
            펌웨어와 회로도 대조 검사
          </span>
        </Link>

        <div className="flex items-center gap-x-1">
          <SessionLinks />
        </div>

        {meta && meta.length > 0 && (
          // 좁은 화면에서는 메타를 숨긴다. 같은 값이 리포트 본문에 다시 나온다
          <dl className="hidden items-center gap-2 sm:flex">
            {meta.map((m) => (
              <div
                key={m.label}
                className="flex items-baseline gap-1.5 rounded-chip bg-surface-2 px-2.5 py-1.5"
              >
                <dt className="text-[12px] font-semibold text-mute">
                  {m.label}
                </dt>
                <dd className="data text-[12px] text-sub">{m.value}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </header>
  );
}

/**
 * 로그인 상태 표시.
 *
 * **로그아웃 상태에서도 아무것도 막지 않는다.** 여기 있는 건 링크뿐이다.
 * 확인 중일 때는 아무것도 안 그린다 — 새로고침마다 "로그인"이 잠깐 떴다
 * 사라지면 그건 깜빡임으로 보인다.
 */
function SessionLinks() {
  const { user, loading, signOut } = useSession();

  if (loading) return null;

  if (!user) {
    return (
      <Link
        to="/login"
        className="inline-flex min-h-[44px] items-center rounded-block px-3 text-[14px] font-bold text-sub transition hover:text-ink"
      >
        로그인
      </Link>
    );
  }

  return (
    <>
      <Link
        to="/mine"
        className="inline-flex min-h-[44px] items-center rounded-block px-3 text-[14px] font-bold text-sub transition hover:text-ink"
      >
        내 검사
      </Link>
      <button
        type="button"
        onClick={() => void signOut()}
        className="inline-flex min-h-[44px] items-center rounded-block px-3 text-[14px] font-semibold text-mute transition hover:text-ink"
      >
        로그아웃
      </button>
    </>
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
export function SectionTitle({
  no,
  children,
}: {
  no: string;
  children: React.ReactNode;
}) {
  return (
    <h2 className="mb-4 flex items-baseline gap-2">
      <span className="data text-[13px] text-mute">{no}</span>
      <span className="text-[19px] font-bold">{children}</span>
    </h2>
  );
}
