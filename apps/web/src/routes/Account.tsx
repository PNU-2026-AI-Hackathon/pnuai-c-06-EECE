import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { GithubAuthButton, githubErrorMessage } from "../components/GithubAuthButton";
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
/**
 * 비밀번호 최소 길이.
 *
 * **서버(`web/auth.py`의 `MIN_PASSWORD_LENGTH`)가 진실이고 여기는 사본이다.**
 * 화면이 더 느슨하면 사용자가 다 치고 나서 거절당하고, 더 빡빡하면
 * 쓸 수 있는 비밀번호를 막는다. 서버 값을 바꾸면 여기도 같이 바꾼다.
 */
const MIN_PASSWORD = 10;

export function AccountPage({ mode }: { mode: "login" | "signup" }) {
  const navigate = useNavigate();
  const { setUser, storage, github } = useSession();

  // GitHub 콜백이 실패하면 `?error=` 를 달고 이 화면으로 돌아온다.
  // **`fetch` 가 아니라 주소창으로 오는 오류**라 state 로는 못 받는다.
  const [params] = useSearchParams();
  const fromGithub = githubErrorMessage(params.get("error"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
        {/*
          **토스 라이팅 원칙 2「잡초 자르기」** — 넣든 빼든 뜻이 안 바뀌는 말을 없앤다.
          전에는 "내 것으로 남고, 나만 볼 수 있고, 직접 내릴 수 있습니다" 였는데
          가운데는 **사실도 아니었다** (결과 링크는 주소를 알면 열린다).

          남긴 것은 **사용자가 지금 결정하는 데 필요한 것 둘**이다 —
          무엇이 필요한가, 돈이 드는가.
        */}
        <p className="mb-8 text-[15px] leading-relaxed text-sub">
          {joining ? (
            <>
              이메일과 비밀번호만 있으면 됩니다.{" "}
              <strong className="font-bold text-ink">카드 등록은 필요 없습니다.</strong>
            </>
          ) : (
            <>이메일과 비밀번호를 입력해 주세요.</>
          )}
        </p>

        {/*
          **GitHub 을 폼 위에 둔다.** 아래에 두면 "안 되면 이것도 있어요" 로 읽히는데,
          우리 사용자는 거의 다 GitHub 계정이 있고 CI 연동도 결국 그 위에서 돈다.
          먼저 보이는 것이 권하는 길이다.

          서버에 GitHub 앱이 설정돼 있지 않으면 이 블록은 **통째로 안 그려진다.**
        */}
        {github?.enabled && (
          <>
            <GithubAuthButton />
            <div className="my-7 flex items-center gap-4">
              <span className="h-px flex-1 bg-line" />
              <span className="text-[13px] font-bold text-mute">또는</span>
              <span className="h-px flex-1 bg-line" />
            </div>
          </>
        )}

        {fromGithub && (
          <p
            role="alert"
            className="mb-6 rounded-block border border-crit/20 bg-crit-weak px-4 py-3 text-[14px] leading-relaxed text-ink"
          >
            {fromGithub}
          </p>
        )}

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
          <div className="relative">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete={joining ? "new-password" : "current-password"}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-block border border-line bg-surface py-3 pl-4 pr-16 text-[15px] outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20"
            />
            {/*
              **보기 토글.** 비밀번호 UI 조사에서 첫 번째로 꼽히는 항목이고,
              오타로 인한 로그인 실패를 가장 많이 줄인다. 긴 비밀번호를 권할수록 더 필요하다.
            */}
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-pressed={showPassword}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-block px-3 py-2 text-[13px] font-bold text-mute transition hover:text-sub"
            >
              {showPassword ? "숨기기" : "보기"}
            </button>
          </div>
          {/*
            **규칙을 입력 중에 알려준다.** 정적인 안내문은 다 치고 나서야 틀린 걸 알게 한다.
            전에는 "10자 이상. 기억하기 쉬운 문장이면 됩니다." 였는데, 뒷문장은 규칙이
            아니라 조언이라 사용자가 지금 할 일을 안 알려준다 (잡초).
          */}
          {joining && (
            <p
              className={`mt-2 text-[13px] transition ${
                password.length === 0
                  ? "text-mute"
                  : password.length >= MIN_PASSWORD
                    ? "text-ok"
                    : "text-mute"
              }`}
            >
              {password.length === 0
                ? `${MIN_PASSWORD}자 이상`
                : password.length >= MIN_PASSWORD
                  ? `${MIN_PASSWORD}자 이상 · 사용할 수 있습니다`
                  : `${MIN_PASSWORD}자 이상 · ${MIN_PASSWORD - password.length}자 더 필요합니다`}
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
            {/*
              **이 문장은 GitHub 이 켜지면 절반이 해결된다.** 비밀번호를 안 만들면
              잊을 것도 없다. 그 사실을 안 말하면, 우리가 이미 제공하는 해결책을
              두고 사용자에게 경고만 주는 셈이다.
            */}
            <p>
              비밀번호를 잊으면 계정을 되찾을 수 없습니다.{" "}
              {github?.enabled
                ? "GitHub으로 시작하시면 비밀번호를 만들지 않습니다."
                : "비밀번호 관리자에 저장해 두세요."}
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

        {/*
          **「바로 검사하기」를 지웠다.** 로그인 벽이 생기면서 그 링크는 여기로 되돌아온다 —
          가입하려는 사람에게 "안 해도 된다" 고 말했다가 다시 데려오는 셈이었다.
        */}
        <p className="mt-4 text-[13.5px] leading-relaxed text-mute">
          가입하시면{" "}
          <Link to="/privacy" className="font-semibold text-sub hover:text-ink underline">
            데이터 처리 안내
          </Link>
          에 동의하는 것으로 봅니다. 받는 것은 이메일 주소 하나뿐입니다.
        </p>
      </main>
    </div>
  );
}
