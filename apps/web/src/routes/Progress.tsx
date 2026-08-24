import { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router-dom";

import { Page, SectionTitle } from "../components/Layout";
import { Pipeline } from "../components/Pipeline";
import { ApiFailure, getCheck } from "../lib/api";
import type { CheckResult } from "../types/api";

/** 처리 중 — 1초마다 결과를 물어보고 done이 되면 리포트로 넘긴다 */
export function ProgressPage() {
  const { id = "" } = useParams();
  const [check, setCheck] = useState<CheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    let timer: number;

    const poll = async () => {
      try {
        const next = await getCheck(id);
        if (!alive) return;
        setCheck(next);
        if (next.status === "running") timer = window.setTimeout(poll, 1000);
      } catch (e) {
        // 서버 문구를 그대로 보여준다
        if (alive)
          setError(
            e instanceof ApiFailure
              ? e.message
              : "결과를 가져오지 못했습니다. 연결을 확인해 주세요."
          );
      }
    };

    void poll();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [id]);

  if (check?.status === "done") return <Navigate to={`/r/${id}`} replace />;

  return (
    <Page meta={[{ label: "검사", value: id }, { label: "상태", value: check?.status ?? "조회 중" }]}>
      {/* 리포트와 같은 이유로 `h1` 이 필요하다 — 화면 낭독 시 무슨 화면인지 알 수 없었다 */}
      <h1 className="mb-6 text-[24px] font-extrabold leading-snug tracking-tight md:text-[30px]">
        검사하는 중입니다
      </h1>

      <SectionTitle no="02">진행</SectionTitle>

      {error && (
        <p role="alert" className="rounded-block bg-crit-weak px-4 py-3 text-[14px] font-semibold text-crit">
          {error}
        </p>
      )}

      {!check && !error && <p className="text-[15px] text-mute">검사를 불러오는 중입니다.</p>}

      {check && <Pipeline steps={check.pipeline} running={check.status === "running"} />}

      {check?.status === "failed" && (
        <p role="alert" className="mt-4 rounded-block bg-crit-weak px-4 py-3 text-[14px] font-semibold text-crit">
          검사가 중단되었습니다. 위 단계에서 실패 표시된 항목을 확인해 주세요.
        </p>
      )}
    </Page>
  );
}
