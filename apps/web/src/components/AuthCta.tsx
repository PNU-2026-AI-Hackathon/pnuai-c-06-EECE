import { Link } from "react-router-dom";

import { useSession } from "../lib/session";

/**
 * 랜딩의 큰 버튼 한 쌍. **로그인했는지에 따라 목적지가 바뀐다.**
 *
 * 로그인한 사람에게 「무료로 시작하기」와 「로그인」을 보여주고 있었다.
 * 이미 가입한 사람에게 가입하라고 하는 화면이었다 — 눌러 봐야 자기 계정으로
 * 되돌아온다.
 *
 * **버튼을 감추지 않고 목적지만 바꾼다.** 로그인했다고 자리를 비우면 그 사람은
 * 랜딩에서 할 일이 없어진다. 자리는 그대로 두고 「다음에 할 일」로 바꾼다 —
 * 아직 검사 안 한 사람에게는 가입, 이미 가입한 사람에게는 검사다.
 *
 * `loading` 중에는 아무것도 안 그린다. 헤더(`Layout.tsx` 의 `SessionLinks`)와
 * 같은 규칙이다. 이걸 안 지키면 새로고침마다 「무료로 시작하기」가 한 번 떴다가
 * 「검사 시작하기」로 바뀌면서 깜빡인다.
 */
export function AuthCta() {
  const { user, loading } = useSession();

  // 두 버튼 높이만큼 자리를 잡아 둔다 — 안 그러면 나타날 때 아래 내용이 밀린다
  if (loading) return <div className="min-h-[52px]" aria-hidden="true" />;

  const [primary, secondary] = user
    ? ([
        { to: "/check", label: "검사 시작하기" },
        { to: "/mine", label: "내 검사" },
      ] as const)
    : ([
        { to: "/signup", label: "무료로 시작하기" },
        { to: "/login", label: "로그인" },
      ] as const);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Link to={primary.to} className="btn-primary">
        {primary.label}
      </Link>
      <Link
        to={secondary.to}
        className="inline-flex min-h-[44px] items-center rounded-block px-3 text-[15px] font-bold text-sub hover:text-ink"
      >
        {secondary.label}
      </Link>
    </div>
  );
}
