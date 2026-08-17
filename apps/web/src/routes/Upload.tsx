import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Page, SectionTitle } from "../components/Layout";
import { SourceMark } from "../components/Mark";
import { ApiFailure, createCheck, sampleCheck, usingMock } from "../lib/api";

/** 슬롯 하나 — 드래그앤드롭과 파일 선택 버튼을 둘 다 제공한다 */
function Slot({
  title,
  required,
  accept,
  file,
  onPick,
  missingNote,
}: {
  title: string;
  required?: boolean;
  accept: string;
  file: File | null;
  onPick: (f: File | null) => void;
  /** 비었을 때 무엇을 못 하게 되는지 */
  missingNote?: string;
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
        <SourceMark known={file !== null} />
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
          {missingNote && <p className="mb-4 text-[13px] leading-relaxed text-warn">{missingNote}</p>}
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
      setError(e instanceof ApiFailure ? e.message : "검사를 시작하지 못했습니다.");
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
          accept=".d356,.ipc,.txt"
          file={netlist}
          onPick={setNetlist}
        />
        <Slot
          title="부품 목록"
          accept=".csv"
          file={bom}
          onPick={setBom}
          missingNote="없으면 부품 식별 불가 · 오탐 증가"
        />
        <Slot
          title="펌웨어"
          accept=".zip"
          file={firmware}
          onPick={setFirmware}
          missingNote="없으면 코드 대조 규칙 5개 실행 불가"
        />
      </div>

      {/* 표기법을 여기서 한 번 가르친다. 리포트의 소스 레인이 같은 기호를 쓴다 */}
      <p className="mb-8 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-mute">
        <SourceMark known />
        <span>제출됨</span>
        <span className="text-line">·</span>
        <SourceMark known={false} />
        <span>없음 — 리포트에서 "모름"으로 남습니다</span>
      </p>

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
        <button
          type="button"
          onClick={() => navigate(`/r/${sampleCheck.check_id}`)}
          className="btn-ghost"
        >
          샘플 보드로 실행
        </button>
      </div>

      {usingMock && (
        <p className="mt-8 rounded-block bg-surface-2 px-4 py-3.5 text-[13px] leading-relaxed text-sub">
          지금은 백엔드 없이 목 데이터로 동작합니다. 샘플 결과는 실제 보드
          <span className="data"> esp32c6presencesmartlight.d356 </span>
          를 파서와 규칙 엔진에 돌려 얻은 값입니다.
        </p>
      )}
    </Page>
  );
}
