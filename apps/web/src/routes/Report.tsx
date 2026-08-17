import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { FindingCard } from "../components/FindingCard";
import { Page, SectionTitle } from "../components/Layout";
import { NetlistAppendix } from "../components/NetlistAppendix";
import { Pipeline } from "../components/Pipeline";
import { InputsTable, SummaryTiles } from "../components/Summary";
import { getCheck } from "../lib/api";
import type { CheckResult } from "../types/api";

/**
 * 리포트. 구조는 Lighthouse를 따른다.
 * 해제된 항목(PASS)은 접어서 하단에 둔다 — 문제부터 보여야 한다.
 */
export function ReportPage() {
  const { id = "" } = useParams();
  const [check, setCheck] = useState<CheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCheck(id)
      .then(setCheck)
      .catch(() => setError("검사 결과를 찾지 못했습니다."));
  }, [id]);

  if (error) {
    return (
      <Page>
        <p role="alert" className="rounded-block bg-crit-weak px-4 py-3 text-[14px] font-semibold text-crit">
          {error}{" "}
          <Link to="/" className="underline decoration-crit/40">
            처음으로
          </Link>
        </p>
      </Page>
    );
  }

  if (!check) {
    return (
      <Page>
        <p className="text-[15px] text-mute">리포트를 불러오는 중입니다.</p>
      </Page>
    );
  }

  const open = check.findings.filter((f) => f.verdict !== "PASS");
  const cleared = check.findings.filter((f) => f.verdict === "PASS");

  return (
    <Page
      meta={[
        { label: "검사", value: check.check_id },
        { label: "보드", value: check.inputs.netlist?.filename.replace(/\.[^.]+$/, "") ?? "—" },
        { label: "생성", value: check.created_at.slice(0, 10) },
      ]}
    >
      <SectionTitle no="01">요약</SectionTitle>
      <div className="mb-8">
        <SummaryTiles summary={check.summary} />
        {check.summary.rules_skipped > 0 && (
          <p className="mt-3 rounded-block bg-warn-weak px-4 py-3.5 text-[14px] leading-relaxed text-warn">
            규칙 {check.summary.rules_skipped}개는 입력이 부족해 실행하지 못했습니다. 아래 진행
            단계에서 사유를 확인하세요.{" "}
            <strong className="font-bold">돌리지 못한 규칙은 "이상 없음"이 아닙니다.</strong>
          </p>
        )}
      </div>

      <SectionTitle no="02">입력</SectionTitle>
      <div className="mb-8">
        <InputsTable inputs={check.inputs} summary={check.summary} />
      </div>

      <SectionTitle no="03">진행 단계</SectionTitle>
      <div className="mb-8">
        <Pipeline steps={check.pipeline} />
      </div>

      <SectionTitle no="04">발견 {open.length}건</SectionTitle>
      <div className="mb-8 space-y-4">
        {open.length === 0 ? (
          <p className="card px-5 py-8 text-center text-[15px] text-sub">
            실행한 규칙에서는 어긋남을 찾지 못했습니다. 실행하지 못한 규칙이 남아 있다면 위를
            확인하세요.
          </p>
        ) : (
          open.map((f, i) => <FindingCard key={`${f.rule}-${f.net}-${i}`} finding={f} />)
        )}
      </div>

      {cleared.length > 0 && (
        <details className="card mb-8 overflow-hidden">
          <summary className="cursor-pointer px-5 py-4 text-[15px] font-bold text-sub">
            해제된 항목 {cleared.length}건
          </summary>
          <div className="space-y-4 border-t border-line bg-bg p-4">
            {cleared.map((f, i) => (
              <FindingCard key={`${f.rule}-${f.net}-${i}`} finding={f} />
            ))}
          </div>
        </details>
      )}

      <SectionTitle no="05">부록 · 넷리스트</SectionTitle>
      <NetlistAppendix netlist={check.netlist} />
    </Page>
  );
}
