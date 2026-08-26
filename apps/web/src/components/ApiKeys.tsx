import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiFailure, createKey, fetchKeys, revokeKey } from "../lib/api";
import { useSession } from "../lib/session";
import type { ApiKey } from "../types/api";

/**
 * API 키 관리.
 *
 * ## 이 화면이 지켜야 하는 것 하나
 *
 * **원문은 만들 때 한 번만 존재한다.** 서버에도 SHA-256 만 남아서, 이 화면을
 * 닫으면 아무도 되찾을 수 없다.
 *
 * 그래서 두 가지를 지킨다 —
 *
 * 1. **만들기 전에** 말한다. 다 만들고 나서 "복사해 두셨어야 합니다"는 속인 것이다
 * 2. 새로 나온 키는 **사용자가 닫기 전까지 안 사라진다.** 다른 조작(목록 새로고침
 *    같은 것)으로 화면에서 밀려나면 그 키는 그대로 죽는다
 *
 * ## 마지막 사용 시각을 보여주는 이유
 *
 * 「이 키 아직 쓰이나?」를 모르면 무서워서 아무도 안 지운다. 그러면 방치된 키가
 * 쌓이고, 하나가 새는 날 피해가 커진다. **지울 수 있게 하려면 알려줘야 한다.**
 */
export function ApiKeys() {
  const { github } = useSession();
  const [keys, setKeys] = useState<ApiKey[] | null>(null);
  const [max, setMax] = useState(0);
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** 방금 만든 키의 원문. **사용자가 닫기 전까지 유지한다.** */
  const [fresh, setFresh] = useState<{ label: string; token: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetchKeys();
      setKeys(res.keys);
      setMax(res.max);
    } catch (failure) {
      setError(failure instanceof ApiFailure ? failure.message : "키 목록을 불러오지 못했습니다.");
      setKeys([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function make(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await createKey(label);
      setFresh({ label: created.label, token: created.token });
      setLabel("");
      await load();
    } catch (failure) {
      setError(failure instanceof ApiFailure ? failure.message : "키를 만들지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setError(null);
    try {
      await revokeKey(id);
      setKeys((current) => (current ?? []).filter((k) => k.id !== id));
    } catch (failure) {
      setError(failure instanceof ApiFailure ? failure.message : "키를 지우지 못했습니다.");
    }
  }

  const full = keys !== null && max > 0 && keys.length >= max;

  return (
    <section className="mt-12 border-t border-line pt-10">
      <h2 className="mb-2 text-[19px] font-extrabold tracking-tight md:text-[22px]">API 키</h2>
      <p className="mb-6 max-w-2xl text-[14.5px] leading-relaxed text-sub">
        화면 없이 검사를 돌릴 때 씁니다. CI 나 스크립트에서 이 키로 인증합니다.
      </p>

      {/* 방금 만든 키 — 여기가 원문이 존재하는 유일한 순간이다 */}
      {fresh && <FreshKey value={fresh} onClose={() => setFresh(null)} />}

      {error && (
        <p
          role="alert"
          className="mb-5 rounded-block border border-crit/20 bg-crit-weak px-4 py-3 text-[14px] leading-relaxed text-ink"
        >
          {error}
        </p>
      )}

      {keys === null ? (
        <p className="text-[15px] text-mute">불러오는 중…</p>
      ) : keys.length === 0 ? (
        <p className="mb-6 text-[15px] text-sub">아직 만든 키가 없습니다.</p>
      ) : (
        <ul className="mb-6 space-y-3">
          {keys.map((key) => (
            <li
              key={key.id}
              className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-card border border-line bg-surface px-5 py-4"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-[15px] font-bold text-ink">{key.label}</p>
                <p className="mt-1 text-[13px] text-mute">
                  {formatWhen(key.created_at)}에 만듦 ·{" "}
                  {/*
                    **「한 번도 안 쓰임」을 흐리게 하지 않는다.** 그게 지워도 되는
                    키라는 가장 강한 신호다.
                  */}
                  {key.last_used_at
                    ? `마지막 사용 ${formatWhen(key.last_used_at)}`
                    : "한 번도 쓰이지 않았습니다"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => remove(key.id)}
                className="min-h-[40px] rounded-chip px-3 text-[13px] font-bold text-mute transition hover:bg-surface-2 hover:text-crit"
              >
                지우기
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={make} className="flex flex-wrap items-end gap-3">
        <div className="min-w-[220px] flex-1">
          <label className="mb-1.5 block text-[13px] font-bold text-sub" htmlFor="key-label">
            어디에 쓰는 키인가요?
          </label>
          <input
            id="key-label"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="CI 러너"
            required
            disabled={full}
            className="w-full rounded-block border border-line bg-surface px-4 py-3 text-[15px] outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20 disabled:opacity-50"
          />
        </div>
        <button type="submit" disabled={busy || full} className="btn-primary disabled:opacity-50">
          {busy ? "만드는 중…" : "키 만들기"}
        </button>
      </form>

      {/*
        **만들기 전에 말한다.** 다 만들고 나서 "복사해 두셨어야 합니다" 라고 하면
        그건 알려준 것이 아니라 속인 것이다 (헌법 2-4).
      */}
      <p className="mt-3 text-[13.5px] leading-relaxed text-mute">
        만든 키는 <strong className="font-bold text-sub">그 자리에서 한 번만 보입니다.</strong>{" "}
        저희 서버에도 원문이 남지 않아서, 잃어버리면 새로 만드셔야 합니다.
      </p>
      {full && (
        <p className="mt-2 text-[13.5px] text-warn">
          키는 {max}개까지 만들 수 있습니다. 안 쓰는 키를 먼저 지워 주세요.
        </p>
      )}

      {/*
        **키를 만든 다음에 뭘 해야 하는지가 여기 없었다.** 키만 손에 쥐어 주고
        "이제 YAML 을 쓰세요" 로 끝내면, 경로를 맞추는 데서 대부분 막힌다.
        그 일을 대신해 주는 화면이 생겼으니 여기서 잇는다.
      */}
      {github?.enabled && (
        <div className="mt-8 rounded-card border border-line bg-surface-2 px-5 py-4">
          <p className="mb-1 text-[14.5px] font-bold text-ink">
            GitHub 저장소에 붙이시겠어요?
          </p>
          <p className="mb-3 text-[13.5px] leading-relaxed text-sub">
            저장소를 훑어 회로도·펌웨어가 어디 있는지 찾고, 경로가 채워진 워크플로 파일을
            PR 로 올려 드립니다.
          </p>
          <Link to="/connect" className="text-[14px] font-bold text-brand-strong hover:underline">
            저장소 연결하기 →
          </Link>
        </div>
      )}
    </section>
  );
}

/** 방금 만든 키. **사용자가 닫을 때까지 안 사라진다.** */
function FreshKey({
  value,
  onClose,
}: {
  value: { label: string; token: string };
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value.token);
      setCopied(true);
    } catch {
      // 클립보드 권한이 없는 브라우저가 실제로 있다. **실패를 삼키지 않는다** —
      // 키는 화면에 그대로 있으므로 직접 긁으면 된다.
      setCopied(false);
    }
  }

  return (
    <div className="mb-6 rounded-card border border-ok/30 bg-ok-weak p-5">
      <p className="mb-1 text-[15px] font-extrabold text-ink">「{value.label}」 키가 만들어졌습니다</p>
      <p className="mb-4 text-[13.5px] leading-relaxed text-sub">
        지금 복사해서 안전한 곳에 두세요. <strong className="font-bold text-ink">이 창을 닫으면 다시 볼 수 없습니다.</strong>
      </p>
      <code className="mb-4 block overflow-x-auto rounded-block bg-surface px-4 py-3 font-mono text-[13.5px] text-ink">
        {value.token}
      </code>
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" onClick={copy} className="btn-primary">
          {copied ? "복사했습니다" : "복사"}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="min-h-[44px] rounded-block px-3 text-[14px] font-bold text-sub hover:text-ink"
        >
          복사했습니다, 닫기
        </button>
      </div>
    </div>
  );
}

/** 못 읽는 값이면 **손대지 않고 그대로 보여준다.** "Invalid Date" 보다 낫다. */
function formatWhen(raw: string): string {
  const when = new Date(raw);
  if (Number.isNaN(when.getTime())) return raw;
  return when.toLocaleDateString("ko-KR", { year: "numeric", month: "long", day: "numeric" });
}
