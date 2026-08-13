import type { ReactNode } from "react";

import { MockDataBadge } from "@/components/common/mock-data-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

/** 차트에 함께 제공할 표 데이터 */
export interface ChartTableData {
  /** 표 머리글 */
  headers: string[];
  /** 행 데이터 (문자열로 포맷된 값) */
  rows: string[][];
}

/**
 * 차트 공통 틀.
 * 모든 차트는 이 컴포넌트로 감싸 텍스트 대안(표)을 함께 제공한다.
 * tableMode="visible"이면 표를 화면에도 보여주고, "screen-reader"면 스크린리더에만 읽힌다.
 */
export function ChartFrame({
  title,
  description,
  summary,
  table,
  tableMode = "screen-reader",
  isMockData = false,
  action,
  children,
  className,
}: {
  /** 차트 제목 */
  title: string;
  /** 차트 아래 보조 설명 */
  description?: string;
  /** 차트를 한 문장으로 요약한 텍스트 대안 (필수) */
  summary: string;
  /** 차트와 동일한 데이터를 담은 표 */
  table: ChartTableData;
  /** 표를 화면에도 보일지 여부 */
  tableMode?: "visible" | "screen-reader";
  isMockData?: boolean;
  /** 우측 상단 조작 영역 */
  action?: ReactNode;
  /** 차트 본체 */
  children: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("shadow-none", className)}>
      <CardHeader className="flex-row items-start justify-between gap-4 space-y-0 pb-2">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-xl">{title}</CardTitle>
            {isMockData && <MockDataBadge />}
          </div>
          {description && <p className="text-base text-muted-foreground">{description}</p>}
        </div>
        {action}
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 차트는 그림이므로 요약 문장을 대안 텍스트로 제공한다 */}
        <figure className="m-0">
          <div role="img" aria-label={summary}>
            {children}
          </div>
          <figcaption className="sr-only">{summary}</figcaption>
        </figure>

        <div className={tableMode === "visible" ? "" : "sr-only"}>
          <Table>
            <caption className="sr-only">{title} 상세 수치</caption>
            <TableHeader>
              <TableRow>
                {table.headers.map((h, i) => (
                  <TableHead key={h} className={i === 0 ? "" : "text-right"}>
                    {h}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {table.rows.map((row) => (
                <TableRow key={row[0]}>
                  {row.map((cell, i) => (
                    <TableCell key={i} className={i === 0 ? "font-medium" : "tnum text-right"}>
                      {cell}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
