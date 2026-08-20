import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Page, SectionTitle } from "../components/Layout";
import { SourceMark } from "../components/Mark";
import { ApiFailure, createCheck, getRules, sampleCheck, usingMock } from "../lib/api";
import type { RuleInfo } from "../types/api";

/**
 * 이 입력이 없으면 어떤 규칙이 못 도는가.
 *
 * 개수를 **카탈로그에서 세어서** 말한다. 코드에 숫자를 박지 않는다.
 * 규칙이 늘거나 구현 상태가 바뀌면 이 문구도 같이 바뀐다.
 */
type Impact = { blocked: RuleInfo[]; pending: RuleInfo[] };

function impactOf(rules: RuleInfo[] | null, need: "bom" | "firmware"): Impact | null {
  if (!rules) return null;
  const hit = rules.filter((r) => r.needs.includes(need));
  return {
    blocked: hit.filter((r) => r.implemented),
    pending: hit.filter((r) => !r.implemented),
  };
}

function ImpactNote({ impact }: { impact: Impact }) {
  if (impact.blocked.length === 0 && impact.pending.length === 0) return null;

  return (
    <p className="mb-4 text-[12px] leading-relaxed text-mute">
      {impact.blocked.length > 0 && (
        <span className="block">
          실행 못 하는 규칙 {impact.blocked.length}개 —{" "}
          <span className="data">{impact.blocked.map((r) => r.id).join(" · ")}</span>
        </span>
      )}
      {impact.pending.length > 0 && (
        <span className="block">
          이 입력을 쓰는 규칙 {impact.pending.length}개는 아직 구현 전 —{" "}
          <span className="data">{impact.pending.map((r) => r.id).join(" · ")}</span>
        </span>
      )}
    </p>
  );
}

/** 슬롯 하나 — 드래그앤드롭과 파일 선택 버튼을 둘 다 제공한다 */
function Slot({
  title,
  required,
  accept,
  file,
  onPick,
  missingNote,
  impact,
}: {
  title: string;
  required?: boolean;
  accept: string;
  file: File | null;
  onPick: (f: File | null) => void;
  /** 비었을 때 무엇을 못 하게 되는지 — 규칙 개수와 무관한 설명 */
  missingNote?: string;
  /** 규칙 카탈로그로 계산한 영향. 카탈로그가 없으면 null이고, 그때는 개수를 말하지 않는다 */
  impact?: Impact | null;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const f = e.dataTransfer.files[0];
        if (f) onPick(f);
      }}
      className={`flex flex-col rounded-card border p-5 transition ${
        file
          ? "border-line bg-surface shadow-card"
          : "border-dashed border-line bg-surface/60"
      } ${over ? "border-brand bg-brand-weak" : ""}`}
    >
      <div className="mb-3 flex items-center gap-2">
        <SourceMark state={file !== null ? "read" : "unknown"} />
        <span className="text-[15px] font-bold">{title}</span>
        <span
          className={`rounded-chip px-1.5 py-0.5 text-[12px] font-semibold ${
            required ? "bg-brand-weak text-brand-strong" : "bg-surface-2 text-mute"
          }`}
        >
          {required ? "필수" : "선택"}
        </span>
      </div>

      {file ? (
        <>
          <p className="data mb-3 break-all text-sub">{file.name}</p>
          <button
            type="button"
            onClick={() => onPick(null)}
            className="mt-auto self-start rounded-chip px-2.5 py-1.5 text-[13px] font-semibold text-mute hover:bg-surface-2 hover:text-ink"
          >
            비우기
          </button>
        </>
      ) : (
        <>
          {missingNote && (
            <p className="mb-2 text-[13px] leading-relaxed text-warn">{missingNote}</p>
          )}
          {impact && <ImpactNote impact={impact} />}
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            className="sr-only"
            onChange={(e) => onPick(e.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="mt-auto self-start rounded-block bg-surface-2 px-3.5 py-2 text-[14px] font-bold text-ink hover:bg-line"
          >
            파일 선택
          </button>
        </>
      )}
    </div>
  );
}

export function UploadPage() {
  const navigate = useNavigate();
  const [netlist, setNetlist] = useState<File | null>(null);
  const [bom, setBom] = useState<File | null>(null);
  const [firmware, setFirmware] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  /**
   * 카탈로그를 못 받은 것과 애초에 없는 것은 다르다.
   * 못 받았으면 그 사실을 말한다 — 조용히 기능을 잃으면 그게 숨기는 것이다 (CLAUDE.md 2-2).
   */
  const [rules, setRules] = useState<RuleInfo[] | null>(null);
  const [catalogFailed, setCatalogFailed] = useState(false);

  // 카탈로그를 못 받아도 업로드는 막지 않는다. 개수만 안 쓴다
  useEffect(() => {
    let alive = true;
    getRules()
      .then((r) => {
        if (!alive) return;
        setRules(r);
        setCatalogFailed(r === null);
      })
      .catch(() => alive && setCatalogFailed(true));
    return () => {
      alive = false;
    };
  }, []);

  async function run() {
    if (!netlist) {
      setError("넷리스트 파일이 필요합니다.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const created = await createCheck({ netlist, bom, firmware });
      navigate(`/c/${created.check_id}`);
    } catch (e) {
      // 서버가 이유를 말해줬으면 그대로 쓴다. 못 닿은 경우도 api.ts 가 문구를 채워 준다
      setError(
        e instanceof ApiFailure
          ? e.message
          : "검사를 시작하지 못했습니다. 잠시 후 다시 시도해 주세요."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page>
      <section className="mb-10 max-w-2xl">
        <p className="mb-3 text-[14px] font-bold text-brand-strong">보드 발주 전 교차검증</p>
        <h1 className="mb-4 text-[27px] font-extrabold leading-[1.35] md:text-[40px] md:leading-[1.25]">
          회로도만 보는 검사는 이미 있습니다.
          <br className="hidden md:block" />{" "}
          <span className="text-brand-strong">코드까지 보는 검사</span>는 없습니다.
        </h1>
        <p className="text-[16px] leading-relaxed text-sub">
          이미 짜놓은 펌웨어가 바뀐 회로도를 따라가고 있는지 보드 발주 전에 검사합니다. 넷리스트만
          있어도 시작할 수 있고, 부품 목록과 펌웨어가 함께 있으면 더 많이 봅니다.
        </p>
      </section>

      <SectionTitle no="01">입력</SectionTitle>
      <div className="mb-4 grid gap-3 md:grid-cols-3">
        <Slot
          title="넷리스트"
          required
          accept=".d356,.ipc,.txt,.xml,.net"
          file={netlist}
          onPick={setNetlist}
        />
        <Slot
          title="부품 목록"
          accept=".csv"
          file={bom}
          onPick={setBom}
          missingNote="없으면 부품을 식별할 수 없어 데이터시트 판정이 전부 보류됩니다."
          impact={impactOf(rules, "bom")}
        />
        <Slot
          title="펌웨어"
          accept=".zip"
          file={firmware}
          onPick={setFirmware}
          missingNote="없으면 코드가 핀을 어떻게 쓰는지 대조할 수 없습니다."
          impact={impactOf(rules, "firmware")}
        />
      </div>

      {/* 표기법을 여기서 한 번 가르친다. 리포트의 소스 레인이 같은 기호를 쓴다 */}
      <p className="mb-8 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-mute">
        <SourceMark state="read" />
        <span>제출됨</span>
        <span className="text-line">·</span>
        <SourceMark state="unknown" />
        <span>없음 — 리포트에서 "모름"으로 남습니다</span>
      </p>

      {catalogFailed && (
        <p className="mb-6 rounded-block bg-warn-weak px-4 py-3.5 text-[13px] leading-relaxed text-warn">
          규칙 목록을 불러오지 못했습니다. 그래서{" "}
          <strong className="font-bold">"규칙 몇 개가 못 돈다"는 개수를 표시하지 않습니다.</strong>{" "}
          검사 자체는 정상 동작합니다.
        </p>
      )}

      {error && (
        <p
          role="alert"
          className="mb-4 rounded-block bg-crit-weak px-4 py-3 text-[14px] font-semibold text-crit"
        >
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2.5">
        <button type="button" onClick={run} disabled={busy} className="btn-primary">
          {busy ? "시작하는 중" : "검사 실행"}
        </button>
        {/*
          **파일이 없는 사람에게 유일한 입구다.**

          한동안 `usingMock` 으로 가려 뒀다. 서버가 이 id 를 몰라서 404 가 났기 때문이고,
          "서버가 샘플을 직접 만들어 주면 되살린다" 고 적어 뒀다 (백엔드_요청서 F-4).
          **그 F-4 가 끝났는데 이 조건이 안 따라왔다** — 정확히 우리가 잡으려는 종류의
          드리프트였고, 배포된 화면에서만 버튼이 사라져 있었다.

          양쪽 id 가 `chk_sample01` 로 같아서 목이든 서버든 그대로 열린다.
          `tests/test_samples.py` 와 `scripts/smoke.sh` 6단계가 그 사실을 지킨다.
        */}
        <button
          type="button"
          onClick={() => navigate(`/r/${sampleCheck.check_id}`)}
          className="btn-ghost"
        >
          예시 보드 결과 보기
        </button>
      </div>

      {usingMock && (
        <p className="mt-8 rounded-block bg-surface-2 px-4 py-3.5 text-[13px] leading-relaxed text-sub">
          지금은 검사 서버 없이 샘플 데이터로 동작합니다. 결과는 실제 보드
          <span className="data"> esp32c6presencesmartlight.d356 </span>
          를 파서와 규칙 엔진에 돌려 얻은 값이고, 위 규칙 개수는 규칙 목록에서 뽑아 준{" "}
          <span className="data">mocks/rules.json</span> 을 세어서 표시합니다.{" "}
          <strong className="font-bold text-ink">둘 다 손으로 적은 값이 아닙니다.</strong>
        </p>
      )}
    </Page>
  );
}
