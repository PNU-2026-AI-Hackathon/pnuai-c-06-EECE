import { githubStartUrl } from "../lib/api";
import { useSession } from "../lib/session";

/**
 * GitHub 으로 로그인.
 *
 * ## 이 버튼이 지키는 것 하나
 *
 * **서버가 못 하는 일을 버튼으로 만들지 않는다.** GitHub 앱이 설정되지 않은
 * 서버에서는 이 주소가 404 다. 그래서 `github.enabled` 가 참일 때만 그린다 —
 * 눌러 봐야 안 되는 버튼은 없는 것보다 나쁘다 (헌법 2-2).
 *
 * 확인 중(`null`)에도 안 그린다. 「모른다」와 「된다」는 다르다.
 *
 * ## 왜 「계속하기」인가
 *
 * 이 버튼 하나가 **로그인과 가입을 같이** 한다 — 처음이면 계정이 생기고
 * 아니면 그냥 들어온다. 사용자는 자기가 어느 쪽인지 모르는 채로 누르는데
 * 「로그인」이라고 적으면 처음 온 사람이 "나는 계정이 없는데" 하고 멈춘다.
 * 「계속하기」는 양쪽 모두에 참이다.
 *
 * ## `<a>` 인 이유
 *
 * OAuth 는 사용자를 GitHub 으로 **실제로 보냈다가** 데려오는 흐름이라
 * `fetch` 로는 성립하지 않는다. 주소창이 움직여야 한다.
 */
export function GithubAuthButton({ next = "/mine" }: { next?: string }) {
  const { github } = useSession();
  const href = githubStartUrl(next);

  if (!github?.enabled || !href) return null;

  return (
    <a
      href={href}
      className="flex min-h-[52px] w-full items-center justify-center gap-2.5 rounded-block border border-line bg-surface px-6 text-[15px] font-bold text-ink transition hover:bg-surface-2"
    >
      <GithubMark />
      GitHub으로 계속하기
    </a>
  );
}

/** GitHub 마크. **아이콘 세트를 들이지 않는다** — 이 하나뿐이라 인라인이 맞다. */
function GithubMark() {
  return (
    <svg width="19" height="19" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}

/**
 * 콜백이 실패해서 되돌아온 경우의 문구.
 *
 * **서버가 보낸 코드마다 무엇을 하면 되는지가 다르다.** 전부 "다시 시도해
 * 주세요" 로 뭉치면 인증된 이메일이 없는 사람은 영원히 다시 시도한다.
 *
 * 아는 코드가 아니면 `null` 을 준다 — **모르는 것을 지어내지 않는다.**
 */
export function githubErrorMessage(code: string | null): string | null {
  switch (code) {
    case "cancelled":
      return "GitHub 로그인을 취소하셨습니다.";
    case "no_verified_email":
      return "GitHub 계정에 인증된 이메일이 없습니다. GitHub 설정에서 이메일을 인증한 뒤 다시 시도해 주세요.";
    case "github_unreachable":
      return "GitHub에 닿지 못했습니다. 잠시 후 다시 시도해 주세요.";
    case "bad_state":
    case "exchange_failed":
      return "GitHub 로그인을 마치지 못했습니다. 다시 시도해 주세요.";
    default:
      return null;
  }
}
