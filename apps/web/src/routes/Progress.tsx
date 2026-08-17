import { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router-dom";

import { Page, SectionTitle } from "../components/Layout";
import { Pipeline } from "../components/Pipeline";
import { getCheck } from "../lib/api";
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
      } catch {
        if (alive) setError("결과를 가져오지 못했습니다. 검사 주소를 다시 확인해 주세요.");
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
      <SectionTitle no="02">진행</SectionTitle>

      {error && (
        <p role="alert" className="border border-redpen bg-redpen/5 px-4 py-3 text-[14px]">
          {error}
        </p>
      )}

      {!check && !error && <p className="text-[15px] text-graphite">검사를 불러오는 중입니다.</p>}

      {check && <Pipeline steps={check.pipeline} running={check.status === "running"} />}

      {check?.status === "failed" && (
        <p role="alert" className="mt-4 border border-redpen bg-redpen/5 px-4 py-3 text-[14px]">
          검사가 중단되었습니다. 위 단계에서 실패 표시된 항목을 확인해 주세요.
        </p>
      )}
    </Page>
  );
}
