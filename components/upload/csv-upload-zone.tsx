"use client";

import { useRef, useState } from "react";
import { FileSpreadsheet, Upload } from "lucide-react";

import type { UploadResult } from "@/types";

import { UploadSummary } from "@/components/upload/upload-summary";
import { Button } from "@/components/ui/button";
import { CsvParseError, parseSalesCsv } from "@/lib/csv-parse";
import { cn } from "@/lib/utils";

/**
 * 매출 파일 업로드.
 * 백엔드가 없어도 브라우저에서 바로 읽어 결과를 보여준다.
 * 백엔드가 생기면 parseSalesCsv 호출만 fetch로 바꾸면 된다.
 */
export function CsvUploadZone({ storeId }: { storeId: string }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [reading, setReading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setError(null);
    setResult(null);

    if (!/\.(csv|tsv|txt)$/i.test(file.name)) {
      setError(
        file.name.match(/\.xlsx?$/i)
          ? "엑셀 파일은 아직 읽지 못합니다. POS에서 CSV로 내려받아 올려주세요."
          : "CSV 파일만 올릴 수 있습니다."
      );
      return;
    }

    setReading(true);
    try {
      const text = await file.text();
      setResult(parseSalesCsv(text, file.name, storeId));
    } catch (e) {
      setError(
        e instanceof CsvParseError
          ? e.message
          : "파일을 읽는 중 문제가 생겼습니다. 다른 파일로 다시 시도해 주세요."
      );
    } finally {
      setReading(false);
    }
  }

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
          파일을 여기로 끌어다 놓거나 아래 버튼을 눌러 선택하세요. 처음 한 번만 과거 파일을 올리고,
          이후에는 새 파일만 추가하시면 됩니다.
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
        <Button size="lg" className="mt-6" onClick={() => inputRef.current?.click()} disabled={reading}>
          <Upload aria-hidden className="mr-2 size-5" />
          {reading ? "읽는 중입니다" : "파일 선택하기"}
        </Button>

        <p className="mt-4 text-sm text-muted-foreground">
          CSV 파일 · 파일은 사장님 컴퓨터에서 바로 읽으며 어디에도 올라가지 않습니다
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border-2 border-down/40 bg-down-soft p-5">
          <p className="text-lg font-bold">파일을 읽지 못했습니다</p>
          <p className="mt-1 text-base">{error}</p>
        </div>
      )}

      {result && <UploadSummary result={result} />}
    </div>
  );
}
