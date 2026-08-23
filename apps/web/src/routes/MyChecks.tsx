import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Header } from "../components/Layout";
import { ApiFailure, type CheckSummaryRow, deleteCheck, fetchMyChecks } from "../lib/api";
import { useSession } from "../lib/session";

/**
 * 내 검사 목록.
 *
 * 로그인이 실제로 사 주는 것은 두 가지다 — **결과가 남는 것**과
 * **내릴 수 있는 것**. 로그인 전에는 올린 결과를 내릴 방법이 아예 없었다.
 */
export function MyChecksPage() {
  const { user, loading: sessionLoading, storage } = useSession();
  const [rows, setRows] = useState<CheckSummaryRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setRows(await fetchMyChecks());
    } catch (failure) {
      setError(failure instanceof ApiFailure ? failure.message : "목록을 불러오지 못했습니다.");
      setRows([]);
    }
  }, []);

  useEffect(() => {
    if (user) void load();
  }, [user, load]);

  async function remove(id: string) {
    setRemoving(id);
    try {
      await deleteCheck(id);
      setRows((current) => (current ?? []).filter((row) => row.check_id !== id));
    } catch (failure) {
      setError(failure instanceof ApiFailure ? failure.message : "내리지 못했습니다.");
    } finally {
      setRemoving(null);
    }
  }

  if (sessionLoading) {
    return (
      <Shell>
        <p className="text-[15px] text-mute">불러오는 중…</p>
      </Shell>
    );
  }

  if (!user) {
    return (
      <Shell>
        <h1 className="mb-3 text-[26px] font-extrabold tracking-tight">내 검사</h1>
        <p className="mb-6 text-[15px] leading-relaxed text-sub">
          로그인하시면 검사 결과가 여기 남습니다.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link to="/login" className="btn-primary">
            로그인
          </Link>
          <Link
            to="/check"
            className="inline-flex min-h-[44px] items-center rounded-block px-3 text-[15px] font-bold text-sub hover:text-ink"
          >
            로그인 없이 검사하기
          </Link>
        </div>
      </Shell>
    );
  }

  return (
    <Shell>
      <h1 className="mb-2 text-[26px] font-extrabold tracking-tight md:text-[30px]">내 검사</h1>
      <p className="mb-7 text-[15px] leading-relaxed text-sub">
        {user.email} · 여기 있는 결과는 <strong className="font-bold text-ink">나만 볼 수 있습니다.</strong>{" "}
        주소를 아는 사람도 열 수 없습니다.
      </p>

      {storage?.survives_restart === false && (
        <p className="mb-6 rounded-block border border-warn/25 bg-warn-weak px-4 py-3 text-[13.5px] leading-relaxed text-sub">
          이 서버는 아직 영구 저장 장치를 쓰지 않습니다.{" "}
          <strong className="font-bold text-ink">다시 배포하면 아래 목록이 통째로 사라집니다.</strong>{" "}
          남겨야 할 결과는 따로 저장해 두세요.
        </p>
      )}

      {error && (
        <p role="alert" className="mb-5 rounded-block border border-crit/20 bg-crit-weak px-4 py-3 text-[14px] text-ink">
          {error}
        </p>
      )}

      {rows === null ? (
        <p className="text-[15px] text-mute">불러오는 중…</p>
      ) : rows.length === 0 ? (
        <div className="rounded-card border border-line bg-surface p-8 text-center">
          <p className="mb-4 text-[15px] text-sub">아직 검사한 것이 없습니다.</p>
          <Link to="/check" className="btn-primary">
            첫 검사 하기
          </Link>
        </div>
      ) : (
        <ul className="space-y-3">
          {rows.map((row) => (
            <li
              key={row.check_id}
              className="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-card border border-line bg-surface p-5"
            >
              <div className="min-w-0 flex-1">
                <Link
                  to={`/r/${row.check_id}`}
                  className="block truncate text-[15px] font-bold text-ink hover:text-brand-strong"
                >
                  {row.netlist_filename ?? row.check_id}
                </Link>
                <p className="mt-1 text-[13px] text-mute">{formatWhen(row.created_at)}</p>
              </div>
              <div className="flex items-center gap-2">
                <Count n={row.summary?.critical ?? 0} tone="crit" label="치명" />
                <Count n={row.summary?.warning ?? 0} tone="warn" label="경고" />
                <Count n={row.summary?.cleared ?? 0} tone="ok" label="해제" />
              </div>
              <button
                type="button"
                onClick={() => remove(row.check_id)}
                disabled={removing === row.check_id}
                className="min-h-[40px] rounded-chip px-3 text-[13px] font-bold text-mute transition hover:bg-surface-2 hover:text-crit disabled:opacity-50"
              >
                {removing === row.check_id ? "내리는 중…" : "내리기"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-3xl px-5 py-14 md:py-20">{children}</main>
    </div>
  );
}

function Count({ n, tone, label }: { n: number; tone: "crit" | "warn" | "ok"; label: string }) {
  const palette = {
    crit: "bg-crit-weak text-crit",
    warn: "bg-warn-weak text-warn",
    ok: "bg-ok-weak text-ok",
  }[tone];
  return (
    <span
      title={label}
      className={`rounded-chip px-2 py-1 text-[12px] font-extrabold tabular-nums ${
        n === 0 ? "bg-surface-2 text-mute" : palette
      }`}
    >
      {n}
    </span>
  );
}

/** 못 읽는 값이면 **손대지 않고 그대로 보여준다.** "Invalid Date" 보다 낫다. */
function formatWhen(raw: string): string {
  const when = new Date(raw);
  if (Number.isNaN(when.getTime())) return raw;
  return when.toLocaleString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
