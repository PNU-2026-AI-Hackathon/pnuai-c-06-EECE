import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Header } from "../components/Layout";
import { ApiFailure, login, signup } from "../lib/api";
import { useSession } from "../lib/session";

/**
 * 로그인 · 가입.
 *
 * 한 파일에 둘을 같이 둔다. 화면이 거의 같고, 갈라 두면 한쪽만 고치는 일이 생긴다.
 *
 * **이 화면은 없는 기능을 있는 척하지 않는다.** 비밀번호 재설정이 없고
 * (메일 보낼 수단이 없다), 계정이 사라질 수도 있다 (영구 디스크가 없다).
 * 둘 다 가입 버튼 근처에 적는다 — 다 쓰고 나서 알게 되면 그건 속인 것이다.
 */
export function AccountPage({ mode }: { mode: "login" | "signup" }) {
  const navigate = useNavigate();
  const { setUser, storage } = useSession();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const joining = mode === "signup";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const account = joining ? await signup(email, password) : await login(email, password);
      setUser(account);
      navigate("/mine");
    } catch (failure) {
      setError(
        failure instanceof ApiFailure
          ? failure.message
          : "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-md px-5 py-14 md:py-20">
        <h1 className="mb-2 text-[26px] font-extrabold leading-snug tracking-tight md:text-[32px]">
          {joining ? "계정 만들기" : "로그인"}
        </h1>
        <p className="mb-8 text-[15px] leading-relaxed text-sub">
          {joining ? (
            <>
              계정이 있으면 검사 결과가 <strong className="font-bold text-ink">내 것으로 남고</strong>,
              나만 볼 수 있고, 직접 내릴 수 있습니다.
            </>
          ) : (
            <>다시 오신 것을 환영합니다.</>
          )}
        </p>

        <form onSubmit={submit} noValidate>
          <label className="mb-1.5 block text-[13px] font-bold text-sub" htmlFor="email">
            이메일
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mb-5 w-full rounded-block border border-line bg-surface px-4 py-3 text-[15px] outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20"
          />

          <label className="mb-1.5 block text-[13px] font-bold text-sub" htmlFor="password">
            비밀번호
          </label>
          <input
            id="password"
            type="password"
            autoComplete={joining ? "new-password" : "current-password"}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-block border border-line bg-surface px-4 py-3 text-[15px] outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20"
          />
          {joining && (
            <p className="mt-2 text-[13px] leading-relaxed text-mute">
              10자 이상. 기억하기 쉬운 문장이면 됩니다.
            </p>
          )}

          {error && (
            <p
              role="alert"
              className="mt-5 rounded-block border border-crit/20 bg-crit-weak px-4 py-3 text-[14px] leading-relaxed text-ink"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="mt-6 w-full rounded-block bg-brand-strong px-6 py-3.5 text-[15px] font-bold text-white shadow-brand transition hover:brightness-105 disabled:opacity-50"
          >
            {busy ? "잠시만요…" : joining ? "계정 만들기" : "로그인"}
          </button>
        </form>

        {/*
          **경고를 세 블록에서 한 줄로 줄였다.**

          이득 한 문장에 경고가 세 덩어리라 가입 화면이 아니라 면책 고지처럼 읽혔다.
          그렇다고 지우지는 않는다 — 비밀번호를 되살릴 수 없다는 것은 **가입 전에**
          알아야 하고, 다 쓰고 나서 알게 되면 그건 속인 것이다 (헌법 2-4).

          계정 소멸 경고는 **서버가 실제로 재시작을 견디면 저절로 사라진다**
          (`web/storage.py` 가 표식으로 확인한다). 추측으로 안 띄운다.
        */}
        {joining && (
          <div className="mt-6 space-y-2 text-[13px] leading-relaxed text-mute">
            <p>
              비밀번호 재설정 기능이 아직 없습니다. 비밀번호 관리자에 저장해 두세요.
            </p>
            {storage?.survives_restart === false && (
              <p className="rounded-block bg-warn-weak px-3 py-2.5 text-warn">
                지금은 서버를 다시 배포하면 계정과 검사 결과가 지워집니다.
              </p>
            )}
          </div>
        )}

        <p className="mt-8 border-t border-line pt-6 text-[14px] text-sub">
          {joining ? (
            <>
              이미 계정이 있으신가요?{" "}
              <Link to="/login" className="font-bold text-brand-strong hover:underline">
                로그인
              </Link>
            </>
          ) : (
            <>
              계정이 없으신가요?{" "}
              <Link to="/signup" className="font-bold text-brand-strong hover:underline">
                계정 만들기
              </Link>
            </>
          )}
        </p>

        <p className="mt-4 text-[13.5px] leading-relaxed text-mute">
          로그인하지 않아도 검사는 됩니다.{" "}
          <Link to="/check" className="font-semibold text-sub hover:text-ink">
            바로 검사하기
          </Link>{" "}
          ·{" "}
          <Link to="/privacy" className="font-semibold text-sub hover:text-ink">
            데이터 처리 안내
          </Link>
        </p>
      </main>
    </div>
  );
}
