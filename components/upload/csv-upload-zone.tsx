"use client";

import { useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { FileSpreadsheet, Upload } from "lucide-react";

import type { UploadResult } from "@/types";

import { UploadSummary } from "@/components/upload/upload-summary";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** 분석까지 갔는지, 파일만 읽고 멈췄는지 */
type Outcome =
  | { ok: true; upload: UploadResult }
  | { ok: false; reason: string; upload: UploadResult };

/**
 * 매출 파일 업로드.
 *
 * 파일을 /api/analyze 로 보내면 서버가 전체 분석을 만들고, 이후 모든 화면이 이 매장 데이터로 바뀐다.
 * 백엔드(FastAPI)가 생기면 fetch 주소만 바꾸면 된다 — 주고받는 모양은 그대로다.
 */
export function CsvUploadZone({ viewingUpload = false }: { viewingUpload?: boolean }) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  async function handleFile(file: File) {
    setError(null);
    setOutcome(null);

    if (!/\.(csv|tsv|txt)$/i.test(file.name)) {
      setError(
        /\.xlsx?$/i.test(file.name)
          ? "엑셀 파일은 아직 읽지 못합니다. POS에서 CSV로 내려받아 올려주세요."
          : "CSV 파일만 올릴 수 있습니다."
      );
      return;
    }

    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);

      const res = await fetch("/api/analyze", { method: "POST", body: form });
      const data = await res.json();

      if (!res.ok) {
        setError(data.detail ?? "파일을 읽지 못했습니다. 다른 파일로 다시 시도해 주세요.");
        return;
      }

      setOutcome(data);
      // 서버 컴포넌트들이 새 분석 결과를 다시 읽도록 한다
      startTransition(() => router.refresh());
    } catch {
      setError("분석 중 문제가 생겼습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setBusy(false);
    }
  }

  async function restoreSample() {
    setBusy(true);
    await fetch("/api/analyze", { method: "DELETE" });
    setOutcome(null);
    startTransition(() => router.refresh());
    setBusy(false);
  }

  const working = busy || pending;

  return (
    <div className="space-y-5">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files[0];
          if (file) void handleFile(file);
        }}
        className={cn(
          "flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors",
          dragging ? "border-primary bg-brand-soft" : "border-input bg-card"
        )}
      >
        <div className="mb-4 flex size-14 items-center justify-center rounded-full bg-secondary">
          <FileSpreadsheet aria-hidden className="size-7 text-muted-foreground" />
        </div>

        <p className="text-xl font-bold">POS에서 내려받은 매출 파일을 올려주세요</p>
        <p className="mt-2 max-w-md text-base text-muted-foreground">
          파일을 여기로 끌어다 놓거나 아래 버튼을 눌러 선택하세요. 날짜와 금액만 있으면 읽을 수 있고,
          메뉴와 결제 시각이 함께 있으면 더 많은 것을 봐 드립니다.
        </p>

        <input
          ref={inputRef}
          type="file"
          accept=".csv,.tsv,.txt"
          className="sr-only"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
          }}
        />
        <Button size="lg" className="mt-6" onClick={() => inputRef.current?.click()} disabled={working}>
          <Upload aria-hidden className="mr-2 size-5" />
          {working ? "분석하는 중입니다" : "파일 선택하기"}
        </Button>

        <p className="mt-4 text-sm text-muted-foreground">
          CSV 파일 · 파일 자체는 저장하지 않고 분석에만 사용합니다
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border-2 border-down/40 bg-down-soft p-5">
          <p className="text-lg font-bold">파일을 읽지 못했습니다</p>
          <p className="mt-1 text-base">{error}</p>
        </div>
      )}

      {outcome && !outcome.ok && (
        <div role="alert" className="rounded-xl border-2 border-input bg-secondary p-5">
          <p className="text-lg font-bold">파일은 읽었지만 아직 분석은 못 합니다</p>
          <p className="mt-1 text-base">{outcome.reason}</p>
          <p className="mt-2 text-base text-muted-foreground">
            화면은 예시 데이터를 그대로 보여드립니다.
          </p>
        </div>
      )}

      {outcome && <UploadSummary result={outcome.upload} analyzed={outcome.ok} />}

      {(viewingUpload || outcome?.ok) && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border bg-card p-5">
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold">지금 화면은 올리신 파일로 계산하고 있습니다</p>
            <p className="text-base text-muted-foreground">
              예시 매장(장전동 포차)으로 돌아가려면 되돌리기를 눌러주세요.
            </p>
          </div>
          <Button variant="secondary" size="lg" onClick={restoreSample} disabled={working}>
            예시 데이터로 되돌리기
          </Button>
        </div>
      )}
    </div>
  );
}
