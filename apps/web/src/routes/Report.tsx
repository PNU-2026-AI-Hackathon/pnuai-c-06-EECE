import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { FindingCard } from "../components/FindingCard";
import { Page, SectionTitle } from "../components/Layout";
import { NetlistAppendix } from "../components/NetlistAppendix";
import { Pipeline } from "../components/Pipeline";
import { InputsTable, SummaryTiles } from "../components/Summary";
import { ApiFailure, getCheck } from "../lib/api";
import type { CheckResult, Finding, Severity } from "../types/api";

const SEVERITY_ORDER: Record<Severity, number> = { CRITICAL: 0, WARNING: 1, INFO: 2 };

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
      // 서버가 내려준 문구를 그대로 쓴다. 프론트가 다시 지어내지 않는다
      .catch((e) =>
        setError(
          e instanceof ApiFailure ? e.message : "검사 결과를 불러오지 못했습니다. 연결을 확인해 주세요."
        )
      );
  }, [id]);

  if (error) {
    return (
      <Page>
        <div className="card mx-auto max-w-md px-6 py-8 text-center">
          <p role="alert" className="text-[17px] font-bold">
            {error}
          </p>
          <p className="mt-2 text-[14px] leading-relaxed text-sub">
            링크가 오래됐거나 검사 결과가 사라졌을 수 있습니다.
          </p>
          <Link to="/" className="btn-primary mt-6">
            처음으로
          </Link>
        </div>
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

  // 심각도 순으로 보여준다. 같은 심각도 안에서는 서버가 준 순서를 지킨다
  const bySeverity = (a: Finding, b: Finding) =>
    SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];

  const open = check.findings.filter((f) => f.verdict !== "PASS").sort(bySeverity);
  const cleared = check.findings.filter((f) => f.verdict === "PASS").sort(bySeverity);

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
          open.map((f, i) => (
            <FindingCard key={`${f.rule}-${f.net}-${i}`} finding={f} inputs={check.inputs} />
          ))
        )}
      </div>

      {cleared.length > 0 && (
        <details className="card mb-8 overflow-hidden">
          <summary className="cursor-pointer px-5 py-4 text-[15px] font-bold text-sub">
            해제된 항목 {cleared.length}건
          </summary>
          <div className="space-y-4 border-t border-line bg-bg p-4">
            {cleared.map((f, i) => (
              <FindingCard key={`${f.rule}-${f.net}-${i}`} finding={f} inputs={check.inputs} />
            ))}
          </div>
        </details>
      )}

      <SectionTitle no="05">부록 · 넷리스트</SectionTitle>
      <NetlistAppendix netlist={check.netlist} />
    </Page>
  );
}
