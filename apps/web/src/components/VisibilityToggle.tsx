import { useState } from "react";

import { ApiFailure, setVisibility } from "../lib/api";
import type { CheckResult, Visibility } from "../types/api";

/**
 * 이 검사를 주소를 아는 누구나 볼지, 나만 볼지.
 *
 * ## 왜 무료 기능인가
 *
 * 요금표 초안은 이걸 Pro 로 팔고 있었다. **보안을 요금제 뒤에 두면 돈을 안 내는
 * 사람의 회로도를 인질로 잡는 셈이다.** 회로도는 영업비밀인데, 그걸 지키는 값을
 * 따로 받는 제품은 신뢰를 먼저 잃는다. 돈은 자동화(API·CI)와 팀 협업에서 받는다.
 *
 * ## 화면이 말하는 두 문장이 참인 근거
 *
 * 문장을 지어내지 않으려고 **응답의 어느 필드가 보장하는지** 하나씩 확인했다.
 *
 *   "주소를 아는 사람은 누구나 열 수 있습니다"
 *       ← `visibility === "link"`. 서버가 로그인 없이 200 을 준다
 *
 *   "나만 열 수 있습니다"
 *       ← `visibility === "private"`. 서버가 주인 아닌 요청에 404 를 준다
 *
 * **주인에게만 보인다** (`owned`). 남에게 보이면 눌렀을 때 404 를 만난다 —
 * 버튼이 있다는 것 자체가 거짓말이 된다.
 *
 * ## 되돌릴 수 있다
 *
 * 한 번 비공개로 바꾸면 못 돌아가게 하면, 실수로 누른 사람이 링크를 다시 만들어야
 * 한다. 양방향으로 둔다.
 */
export function VisibilityToggle({ check }: { check: CheckResult }) {
  // 옛 응답(목 파일 포함)에는 이 필드가 없다. **없으면 「공개」로 본다** —
  // 지금까지 그렇게 동작해 왔고, 모르는 것을 「비공개」라고 말하면 그게 거짓이다.
  const [visibility, setLocal] = useState<Visibility>(check.visibility ?? "link");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!check.owned) return null;

  const isPrivate = visibility === "private";

  async function flip() {
    const next: Visibility = isPrivate ? "link" : "private";
    setBusy(true);
    setError(null);
    try {
      const res = await setVisibility(check.check_id, next);
      setLocal(res.visibility);
    } catch (failure) {
      setError(
        failure instanceof ApiFailure
          ? failure.message
          : "공개 범위를 바꾸지 못했습니다. 잠시 후 다시 시도해 주세요."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="no-print mb-8 rounded-card border border-line bg-surface px-5 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[15px] font-bold text-ink">
            {isPrivate ? "나만 볼 수 있습니다" : "주소를 아는 사람은 누구나 열 수 있습니다"}
          </p>
          <p className="mt-1 text-[13.5px] leading-relaxed text-sub">
            {isPrivate
              ? "이 주소를 받은 사람도 로그인하지 않으면 열리지 않습니다."
              : "팀에 링크로 보내면 로그인 없이 근거까지 봅니다."}
          </p>
        </div>
        <button
          type="button"
          onClick={flip}
          disabled={busy}
          className="btn-ghost min-h-[44px] shrink-0 disabled:opacity-50"
        >
          {busy ? "바꾸는 중…" : isPrivate ? "링크 공개로 바꾸기" : "나만 보기로 바꾸기"}
        </button>
      </div>

      {/*
        **실패를 삼키지 않는다.** 서버가 거절했는데 화면만 바뀌면, 사용자는
        비공개인 줄 알고 링크를 계속 들고 다닌다. 그게 이 기능에서 가장 나쁜 실패다.
      */}
      {error && (
        <p
          role="alert"
          className="mt-3 rounded-block border border-crit/20 bg-crit-weak px-3 py-2 text-[13.5px] leading-relaxed text-ink"
        >
          {error}
        </p>
      )}
    </div>
  );
}
