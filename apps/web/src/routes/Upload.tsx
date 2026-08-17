import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Page, SectionTitle } from "../components/Layout";
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
      className={`card flex flex-col p-4 ${over ? "border-redpen" : ""}`}
    >
      <div className="mb-2 flex items-baseline gap-2">
        <span className="label text-ink">{title}</span>
        <span className="label">{required ? "필수" : "선택"}</span>
      </div>

      {file ? (
        <>
          <p className="data mb-1 break-all text-ink">{file.name}</p>
          <button
            type="button"
            onClick={() => onPick(null)}
            className="mt-auto self-start border border-hair px-2 py-1 font-cond text-[11px] uppercase tracking-label text-graphite hover:border-ink hover:text-ink"
          >
            비우기
          </button>
        </>
      ) : (
        <>
          {missingNote && <p className="mb-3 text-[13px] text-amber">{missingNote}</p>}
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
            className="mt-auto self-start border border-ink px-3 py-1.5 font-cond text-[12px] uppercase tracking-label hover:bg-ink hover:text-vellum"
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
      <h1 className="mb-2 text-[26px] font-bold leading-snug">
        회로도만 보는 검사는 이미 있습니다.
        <br />
        <span className="text-redpen">코드까지 보는 검사</span>는 없습니다.
      </h1>
      <p className="mb-8 max-w-2xl text-[15px] leading-relaxed text-graphite">
        이미 짜놓은 펌웨어가 바뀐 회로도를 따라가고 있는지 보드 발주 전에 검사합니다.
        넷리스트만 있어도 시작할 수 있고, 부품 목록과 펌웨어가 함께 있으면 더 많이 봅니다.
      </p>

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

      {error && (
        <p role="alert" className="mb-4 border border-redpen bg-redpen/5 px-4 py-3 text-[14px]">
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={run}
          disabled={busy}
          className="border border-ink bg-ink px-5 py-2.5 font-cond text-[13px] uppercase tracking-label text-vellum disabled:opacity-50"
        >
          {busy ? "시작하는 중" : "검사 실행"}
        </button>
        <button
          type="button"
          onClick={() => navigate(`/r/${sampleCheck.check_id}`)}
          className="border border-ink px-5 py-2.5 font-cond text-[13px] uppercase tracking-label hover:bg-ink hover:text-vellum"
        >
          샘플 보드로 실행
        </button>
      </div>

      {usingMock && (
        <p className="mt-6 border-l-2 border-amber pl-3 text-[13px] leading-relaxed text-graphite">
          지금은 백엔드 없이 목 데이터로 동작합니다. 샘플 결과는 실제 보드
          <span className="data"> esp32c6presencesmartlight.d356 </span>
          를 파서와 규칙 엔진에 돌려 얻은 값입니다.
        </p>
      )}
    </Page>
  );
}
