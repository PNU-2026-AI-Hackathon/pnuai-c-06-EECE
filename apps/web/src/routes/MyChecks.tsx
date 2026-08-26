import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiKeys } from "../components/ApiKeys";
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
        {/*
          **이 목록이 비공개인 것과, 결과 링크가 비공개인 것은 다르다.**
          전에는 "주소를 아는 사람도 열 수 없습니다" 라고 적혀 있었는데 **사실이 아니었다** —
          결과 조회는 로그인 없이 열린다(`web/app.py` 의 `get_check`). 공유가 살아 있어야
          해서 그렇게 둔 것이고, 요금 안내도 그렇게 적혀 있다(무료 = 링크 공유).
          같은 사실이 `Privacy.tsx` 에도 있는데 그쪽만 맞고 여기가 틀어져 있었다 (헌법 10절).
        */}
        {user.email} · 이 목록은 <strong className="font-bold text-ink">나에게만 보입니다.</strong>{" "}
        결과는 기본이 링크 공개라 주소를 받은 사람이 열 수 있고,{" "}
        <strong className="font-bold text-ink">결과 화면에서 비공개로 바꾸면 나만 열립니다.</strong>
      </p>

      {storage?.survives_restart === false && (
        <p className="mb-6 rounded-block border border-warn/25 bg-warn-weak px-4 py-3 text-[13.5px] leading-relaxed text-sub">
          {/*
            **사실은 그대로 두고 말투만 바꿨다.**

            전에는 「이 서버는 아직 영구 저장 장치를 쓰지 않습니다」로 시작했다.
            맞는 말이지만 **처음 온 사람에게는 미완성 고백부터 읽힌다.**

            지금 무엇을 하면 되는지를 먼저 말하고, 왜 그런지를 뒤에 둔다.
            숨기는 것은 없다 — 사라진다는 사실은 여전히 굵게 적혀 있다.
          */}
          <strong className="font-bold text-ink">남겨야 할 결과는 링크를 복사해 두세요.</strong>{" "}
          지금은 무료 서버라 <strong className="font-bold text-ink">다시 배포하면 아래 목록이
          사라집니다.</strong> 정식 출시 때 영구 저장으로 바꿉니다.
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

      {/*
        **키 관리를 여기 둔다.** 로그인한 사람만 오는 화면이고, 검사 목록 바로
        아래가 「내 계정에 딸린 것들」이 모이는 자리다. 별도 설정 화면을 새로
        만들면 아무도 안 찾아간다.
      */}
      <ApiKeys />
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
