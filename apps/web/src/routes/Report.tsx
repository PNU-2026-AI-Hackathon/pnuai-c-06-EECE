import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { FindingCard } from "../components/FindingCard";
import { Page, SectionTitle } from "../components/Layout";
import { NetlistAppendix } from "../components/NetlistAppendix";
import { Pipeline } from "../components/Pipeline";
import { InputsTable, SummaryTiles } from "../components/Summary";
import { ApiFailure, checkNotice, getCheck } from "../lib/api";
import type { CheckResult, Finding, Severity } from "../types/api";

const SEVERITY_ORDER: Record<Severity, number> = { CRITICAL: 0, WARNING: 1, INFO: 2 };

/**
 * `created_at` 은 계약상 UTC(`Z`)다. 서버는 시간대를 정하지 않고 화면이 변환한다.
 * 그대로 `slice(0, 10)` 하면 한국 시간 오전 9시 이전 검사가 하루 전 날짜로 보인다.
 */
function toKstDate(iso: string): string {
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return iso.slice(0, 10); // 파싱 못 하면 원문 그대로
  return new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Seoul" }).format(t);
}

/**
 * 리포트. 구조는 Lighthouse를 따른다.
 * 해제된 항목(PASS)은 접어서 하단에 둔다 — 문제부터 보여야 한다.
 */
export function ReportPage() {
  const { id = "" } = useParams();
  const [check, setCheck] = useState<CheckResult | null>(null);
  /** 문구와 함께 코드도 들고 있는다 — 왜 실패했는지에 따라 다음 안내가 달라진다 */
  const [error, setError] = useState<{ message: string; code: string } | null>(null);

  useEffect(() => {
    getCheck(id)
      .then(setCheck)
      // 서버가 내려준 문구를 그대로 쓴다. 프론트가 다시 지어내지 않는다
      .catch((e) =>
        setError(
          e instanceof ApiFailure
            ? { message: e.message, code: e.code }
            : { message: "검사 결과를 불러오지 못했습니다.", code: "UNKNOWN" }
        )
      );
  }, [id]);

  if (error) {
    return (
      <Page>
        <div className="card mx-auto max-w-md px-6 py-8 text-center">
          <p role="alert" className="text-[17px] font-bold">
            {error.message}
          </p>
          {/*
            원인을 단정하지 않는다. 서버가 죽어서 못 불러온 것을 "링크가 오래됐다"고 말하면
            사용자는 멀쩡한 링크를 버린다. 검사를 못 찾은 경우에만 그렇게 안내한다.
          */}
          {error.code === "CHECK_NOT_FOUND" && (
            <p className="mt-2 text-[14px] leading-relaxed text-sub">
              링크가 오래됐거나 검사 결과가 사라졌을 수 있습니다.
            </p>
          )}
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

  /**
   * 발견이 하나도 없는데 그 이유가 "볼 수 없어서"인 경우를 구분한다.
   * 규칙을 다 돌렸고 부품도 식별했는데 0건이면 그건 진짜 "이상 없음"이다.
   */
  const nothingFound =
    check.summary.critical + check.summary.warning + check.summary.cleared === 0;
  const couldNotLook =
    check.summary.rules_skipped > 0 ||
    (check.summary.parts_total > 0 && check.summary.parts_identified === 0);

  const open = check.findings.filter((f) => f.verdict !== "PASS").sort(bySeverity);
  const cleared = check.findings.filter((f) => f.verdict === "PASS").sort(bySeverity);
  const notice = checkNotice(check.check_id);

  return (
    <Page
      meta={[
        { label: "검사", value: check.check_id },
        { label: "보드", value: check.inputs.netlist?.filename.replace(/\.[^.]+$/, "") ?? "—" },
        { label: "생성", value: toKstDate(check.created_at) },
      ]}
    >
      {/* 실제 검사가 아니면 제일 먼저 그 사실을 말한다. 접거나 흐리게 하지 않는다 */}
      {notice && (
        <p
          role="note"
          className="mb-8 rounded-block border border-warn/25 bg-warn-weak px-4 py-3.5 text-[14px] leading-relaxed text-warn"
        >
          <strong className="font-bold">실제 검사 결과가 아닙니다.</strong> {notice}
        </p>
      )}

      <SectionTitle no="01">요약</SectionTitle>
      <div className="mb-8">
        <SummaryTiles summary={check.summary} />

        {/*
          발견 0건은 두 가지 뜻이 될 수 있다 — "검사했고 깨끗함" 과 "볼 수 없어서 못 찾음".
          화면이 그걸 구분하지 않으면 사용자는 전자로 읽는다. 그게 숨기는 것이다 (CLAUDE.md 2-2).
          실제 오픈소스 보드에서 부품 55개 중 0개만 식별된 채 0건이 나온 적이 있다.
        */}
        {nothingFound && couldNotLook && (
          <p className="mt-3 rounded-block bg-crit-weak px-4 py-3.5 text-[14px] leading-relaxed text-crit">
            <strong className="font-bold">발견 0건은 "이상 없음"이 아닙니다.</strong> 이 검사는
            결론을 내리지 못했습니다 — 규칙 {check.summary.rules_total}개 중{" "}
            {check.summary.rules_run}개만 실행됐고
            {check.summary.parts_total > 0 &&
              ` 부품 ${check.summary.parts_total}개 중 ${check.summary.parts_identified}개만 식별됐습니다`}
            . 아래 「어디까지 봤나」에서 무엇이 막혔는지 확인하세요.
          </p>
        )}

        {!(nothingFound && couldNotLook) && check.summary.rules_skipped > 0 && (
          <p className="mt-3 rounded-block bg-warn-weak px-4 py-3.5 text-[14px] leading-relaxed text-warn">
            {/*
              사유를 단정하지 않는다. 못 돈 이유는 "입력 부족"만이 아니라 "미구현"도 있고,
              요약이 가진 숫자로는 둘을 가를 수 없다. 사유는 아래 「어디까지 봤나」가 그대로 말한다.
            */}
            규칙 {check.summary.rules_skipped}개는 실행하지 못했습니다. 아래 「어디까지 봤나」에서 사유를
            확인하세요.{" "}
            <strong className="font-bold">돌리지 못한 규칙은 "이상 없음"이 아닙니다.</strong>
          </p>
        )}
      </div>

      {/*
        **답을 먼저 보여준다.**

        한동안 요약 → 입력 → 진행 단계 → 발견 순서였다. 사용자가 제일 알고 싶은 것
        (무슨 문제가 있나)이 1,150px 아래에 있었다 — 데스크톱에서 1.6화면이다.
        입력과 진행 단계는 **답이 아니라 그 답을 믿어도 되는지**를 말하는 장치라
        답 다음에 와야 한다. 지우지는 않는다 — 못 본 것을 숨기지 않는 것이 이 제품의
        약속이고(헌법 2-4), 위 요약이 이미 "발견 0건은 이상 없음이 아니다"로 그리 보낸다.
      */}
      <SectionTitle no="02">발견 {open.length}건</SectionTitle>
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

      {/* 여기서부터는 **근거 층**이다 — 무엇을 받았고 어디까지 봤는지 */}
      <SectionTitle no="03">검사한 파일</SectionTitle>
      <div className="mb-8">
        <InputsTable inputs={check.inputs} summary={check.summary} />
      </div>

      <SectionTitle no="04">어디까지 봤나</SectionTitle>
      <div className="mb-8">
        <Pipeline steps={check.pipeline} />
      </div>

      <SectionTitle no="05">부록 · 넷리스트</SectionTitle>
      <NetlistAppendix netlist={check.netlist} />
    </Page>
  );
}
