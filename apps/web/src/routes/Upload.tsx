import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

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
    // **규칙 ID 를 나열하지 않는다.** `R01 · R05 · R07 …` 은 우리 내부 어휘라
    // 처음 온 사람에게 아무 뜻이 없고, 아직 아무것도 안 한 화면에서 제일 먼저
    // 눈에 띄면 안 되는 종류의 정보다. 개수만 말하고 무엇인지는 `title` 로 남긴다.
    <p
      className="mb-4 text-[12px] leading-relaxed text-mute"
      title={[...impact.blocked, ...impact.pending].map((r) => `${r.id} ${r.title}`).join("\n")}
    >
      {impact.blocked.length > 0 && (
        <span className="block">검사 항목 {impact.blocked.length}개를 건너뜁니다</span>
      )}
      {impact.pending.length > 0 && (
        <span className="block">{impact.pending.length}개는 아직 준비 중입니다</span>
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
            className="mt-auto inline-flex min-h-[44px] items-center self-start rounded-chip px-3 text-[13px] font-semibold text-mute hover:bg-surface-2 hover:text-ink"
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
            className="mt-auto inline-flex min-h-[44px] items-center self-start rounded-block bg-surface-2 px-4 text-[14px] font-bold text-ink hover:bg-line"
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
  /**
   * 바뀌기 전 회로도. **없어도 검사는 그대로 된다** — R10 만 조용해진다.
   *
   * 한동안 이 슬롯을 일부러 안 뒀다. 근거는 "웹으로 파일을 올리는 사람에게는 이전
   * 넷리스트가 없고, 있는 곳은 CI 다" 였다. 절반은 맞다. 다만 그 대가로
   * **R10 이 화면에서 절대 못 도는 규칙**이 됐다 — 카탈로그에는 「동작」이라 적힌 채로.
   * 회로도를 고친 사람은 직전 판을 가지고 있다. 위 세 칸과 떨어뜨려 둔 것은
   * 처음 오는 사람의 시선을 뺏지 않기 위해서다.
   */
  const [previousNetlist, setPreviousNetlist] = useState<File | null>(null);
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
      const created = await createCheck({ netlist, bom, firmware, previousNetlist });
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
      {/*
        **여기는 검사 화면이다. 다시 설득하지 않는다.**

        홍보는 `/` 가 한다. 파일을 올리러 온 사람에게 히어로와 비교 문구를 또 보이면
        올릴 자리까지 스크롤이 늘어날 뿐이다 — 한동안 그러고 있었다.
      */}
      <section className="mb-8 max-w-2xl">
        <h1 className="mb-2 text-[24px] font-extrabold leading-snug md:text-[30px]">
          검사할 파일을 올려 주세요
        </h1>
        <p className="text-[15px] leading-relaxed text-sub">
          넷리스트만 있어도 시작합니다. 부품 목록과 펌웨어가 함께 있으면 더 많이 봅니다.{" "}
          <Link to={`/r/${sampleCheck.check_id}`} className="font-bold text-brand-strong underline">
            먼저 예시 결과를 보시겠어요?
          </Link>
        </p>
      </section>

      <SectionTitle no="01">검사할 파일</SectionTitle>
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

      {/*
        **드리프트 칸은 따로 둔다.**

        위 세 칸은 "지금 이 보드" 를 검사하는 데 필요한 것이고, 이 칸은 "직전과 무엇이
        달라졌나" 를 묻는 것이라 질문 자체가 다르다. 넷 칸을 나란히 두면 처음 오는
        사람이 넷 다 있어야 하는 줄 안다.
      */}
      <details className="mb-4 rounded-block border border-line bg-surface/60 px-4 py-3">
        <summary className="cursor-pointer select-none text-[14px] font-bold text-ink">
          바뀌기 전 회로도와 비교하기{" "}
          <span className="ml-1 rounded-chip bg-surface-2 px-1.5 py-0.5 text-[12px] font-semibold text-mute">
            선택
          </span>
        </summary>
        <p className="mb-3 mt-3 text-[13px] leading-relaxed text-sub">
          직전 회로도를 함께 올리면 <strong className="font-bold text-ink">무엇이 옮겨갔는지</strong>{" "}
          짚어 줍니다. 한 장만 보면 "이 핀이 안 붙었다" 와 "저 핀을 코드가 안 쓴다" 가 따로
          나오는데, 둘이 같은 사건인지는 이전 상태를 알아야 말할 수 있습니다.
        </p>
        <div className="grid gap-3 md:grid-cols-3">
          <Slot
            title="이전 회로도"
            accept=".d356,.ipc,.txt,.xml,.net"
            file={previousNetlist}
            onPick={setPreviousNetlist}
            missingNote="없으면 무엇이 달라졌는지는 비교하지 않습니다. 리포트에 그렇게 적힙니다."
          />
        </div>
      </details>

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
          **파일을 올리는 자리에서 말한다.** 정책 페이지에만 두면 아무도 안 본다 —
          그리고 이 도구가 받는 것은 남의 회로도와 펌웨어, 곧 지적재산이다.
        */}
        <Link
          to="/privacy"
          className="inline-flex min-h-[44px] items-center rounded-block px-3 text-[13px] text-mute underline hover:text-sub"
        >
          올린 파일은 저장하지 않습니다
        </Link>
        {/*
          예시 보기는 **히어로로 올라갔다.** 파일이 없는 사람이 대부분이라 그 사람의
          유일한 길이 폼 아래 고스트 버튼일 이유가 없다. 여기서 또 내보내면
          같은 화면에 주 행동이 둘이 된다.
        */}
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
