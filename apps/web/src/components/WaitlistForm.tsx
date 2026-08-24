import { useState } from "react";

import { joinWaitlist } from "../lib/api";
import { ApiFailure } from "../lib/api";

/**
 * 「출시 알림 받기」 — **결제를 만들기 전에 살 사람이 있는지 재는 자리.**
 *
 * 요금표가 「준비 중」이라고만 적혀 있는 동안은 방문자가 반응할 대상이 없다.
 * 비싼지 싼지 아무도 말해 주지 않고, 우리는 가격을 정할 근거를 못 얻는다.
 * 가격을 숫자로 공개하고 여기에 이메일을 남기게 하면, 결제 시스템 없이도
 * 그 두 가지를 동시에 얻는다.
 *
 * ## 약속할 수 있는 만큼만 적는다
 *
 * 우리는 아직 **메일 발송 수단이 없다.** 그래서 문구는 "준비되면 이 주소로
 * 알려드립니다" 까지다. 뉴스레터나 할인 안내를 보내겠다고 말하지 않는다 —
 * 보낼 수단이 없는 약속은 지킬 수 없고, 이 제품은 지킬 수 있는 말만 한다.
 */
export function WaitlistForm({ plan, planLabel }: { plan: "pro" | "team"; planLabel: string }) {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "done">("idle");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setState("sending");
    try {
      await joinWaitlist(email, plan);
      setState("done");
    } catch (err) {
      // 서버가 이유를 말해 줬으면 그대로 쓴다 (형식 오류 · 요청 제한)
      setError(
        err instanceof ApiFailure
          ? err.message
          : "지금은 등록하지 못했습니다. 잠시 후 다시 시도해 주세요."
      );
      setState("idle");
    }
  }

  if (state === "done") {
    return (
      <p
        role="status"
        className="mt-5 rounded-block bg-ok-weak px-4 py-3 text-[13.5px] leading-relaxed text-ok"
      >
        <strong className="font-bold">등록했습니다.</strong> {planLabel}가 준비되면 이 주소로
        알려드리겠습니다. 다른 메일은 보내지 않습니다.
      </p>
    );
  }

  return (
    <form onSubmit={submit} className="mt-5 border-t border-line pt-5">
      <label
        htmlFor={`waitlist-${plan}`}
        className="mb-2 block text-[13px] font-bold text-sub"
      >
        출시하면 알려드릴까요?
      </label>
      <div className="flex flex-wrap gap-2">
        <input
          id={`waitlist-${plan}`}
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          autoComplete="email"
          className="min-h-[44px] flex-1 rounded-block border border-line bg-bg px-3 text-[14px] text-ink outline-none focus:border-brand"
        />
        <button
          type="submit"
          disabled={state === "sending"}
          className="btn-ghost min-h-[44px] disabled:opacity-40"
        >
          {state === "sending" ? "등록하는 중" : "알림 받기"}
        </button>
      </div>
      {error && (
        <p role="alert" className="mt-2 text-[13px] font-semibold text-crit">
          {error}
        </p>
      )}
      {/* 받는 것과 안 받는 것을 그 자리에서 말한다 */}
      <p className="mt-2 text-[12.5px] leading-relaxed text-mute">
        이메일 주소 하나만 받습니다. 결제 정보를 받지 않고, 광고 메일을 보내지 않습니다.
      </p>
    </form>
  );
}
