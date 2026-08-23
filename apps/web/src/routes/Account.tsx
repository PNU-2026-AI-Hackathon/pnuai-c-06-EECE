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
              10자 이상이면 됩니다. 대문자·숫자·특수문자를 섞으라고 하지 않습니다 —{" "}
              <strong className="font-semibold text-sub">길이가 훨씬 강합니다.</strong> 기억하기 쉬운
              문장을 쓰셔도 됩니다.
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

        {joining && (
          <div className="mt-7 space-y-3">
            <Caveat head="비밀번호를 잊으면 되돌릴 수 없습니다">
              메일을 보낼 수단이 없어서 재설정 기능을 만들지 못했습니다. 있는 척하지 않겠습니다 —
              비밀번호 관리자에 저장해 두시길 권합니다.
            </Caveat>
            {storage?.survives_restart === false && (
              <Caveat head="계정이 사라질 수 있습니다" tone="warn">
                지금 서버는 영구 저장 장치를 쓰지 않습니다. 다시 배포하면 계정과 검사 결과가 함께
                지워집니다. 이 문구는 서버가 재시작을 견디는 것이 <strong className="font-bold text-ink">실제로
                확인되면</strong> 저절로 사라집니다.
              </Caveat>
            )}
            <Caveat head="이메일은 확인하지 않습니다">
              인증 메일을 보내지 않으므로 이메일은 신원 확인이 아니라 이름표입니다. 받는 메일은
              하나도 없습니다.
            </Caveat>
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

function Caveat({
  head,
  children,
  tone,
}: {
  head: string;
  children: React.ReactNode;
  tone?: "warn";
}) {
  return (
    <div
      className={`rounded-block border p-4 ${
        tone === "warn" ? "border-warn/25 bg-warn-weak" : "border-line bg-surface-2"
      }`}
    >
      <p className="mb-1 text-[13.5px] font-extrabold text-ink">{head}</p>
      <p className="text-[13px] leading-relaxed text-sub">{children}</p>
    </div>
  );
}
