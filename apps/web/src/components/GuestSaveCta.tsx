import { Link } from "react-router-dom";

import { useSession } from "../lib/session";
import type { CheckResult } from "../types/api";

/**
 * 결과를 본 게스트에게 가입을 권한다.
 *
 * ## 왜 여기인가
 *
 * 8/26 에 가입 벽을 **결과 뒤로** 옮겼다. 그러면 이 자리가 새로 생긴 벽의
 * 자리다 — 사람이 이 도구가 무엇을 내놓는지 **이미 본 뒤**다.
 *
 * ## 무엇을 팔고 무엇을 안 파는가
 *
 * **지금 보고 있는 이 결과는 이미 열려 있다.** 주소를 아는 사람은 계속 열 수 있고,
 * 가입한다고 이 화면이 더 좋아지지 않는다. 그러니 "보려면 가입하세요"는 거짓말이다.
 *
 * 가입이 실제로 사 주는 것은 **다음 검사와 목록**이다. 그것만 말한다 (헌법 2-1).
 *
 * ## 언제 안 그리는가
 *
 * - 로그인한 사람 — 이미 계정이 있다
 * - 주인이 있는 검사(`owned`)를 남이 보는 경우 — 남의 결과를 보러 온 사람에게
 *   가입을 권하는 건 맥락이 어긋난다. 링크 공유가 우리 강점인데 그 경험을 흐린다
 * - 확인 중(`loading`) — 깜빡임을 만들지 않는다
 */
/**
 * 이 자리에 가입 권유가 뜨는가.
 *
 * **리포트 아래에는 다음 걸음이 하나만 있어야 한다.** 그래서 「다시 검사하기」 쪽이
 * 이 값을 보고 자리를 비운다 — 조건을 두 곳에 적으면 반드시 갈라진다 (헌법 10절).
 */
export function showsGuestSaveCta(user: unknown, check: CheckResult): boolean {
  return !user && !check.owned;
}

export function GuestSaveCta({ check }: { check: CheckResult }) {
  const { user, loading } = useSession();

  if (loading) return null;
  if (!showsGuestSaveCta(user, check)) return null;

  return (
    <section className="no-print mt-10 rounded-card border border-brand/25 bg-brand/5 px-6 py-5">
      <p className="mb-1.5 text-[16px] font-extrabold text-ink">
        이 결과는 그대로 열려 있습니다
      </p>
      <p className="mb-5 max-w-2xl text-[14.5px] leading-relaxed text-sub">
        주소를 아는 사람은 로그인 없이 이 화면을 봅니다. 가입하지 않으셔도 됩니다.
        <br />
        다만 <strong className="font-bold text-ink">다음 검사부터는 계정이 필요합니다</strong> —
        결과가 목록에 쌓이고, 나중에 다시 찾을 수 있습니다.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <Link to="/signup" className="btn-primary">
          무료로 계정 만들기
        </Link>
        <Link
          to="/login"
          className="inline-flex min-h-[44px] items-center rounded-block px-3 text-[15px] font-bold text-sub hover:text-ink"
        >
          로그인
        </Link>
        <span className="text-[13px] text-mute">이메일 하나면 됩니다 · 카드 등록 없음</span>
      </div>
    </section>
  );
}
