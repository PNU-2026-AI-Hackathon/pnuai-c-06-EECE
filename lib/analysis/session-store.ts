import { cache } from "react";

import type { AnalyzedStore } from "./types";

/**
 * 업로드한 파일의 분석 결과를 담아 두는 자리.
 *
 * ⚠ 서버 프로세스 메모리에만 있습니다. 서버를 재시작하면 사라지고, 여러 명이 동시에 쓸 수 없습니다.
 *   백엔드(FastAPI + DB)가 붙기 전까지 시연을 굴리기 위한 임시 저장소입니다.
 *   백엔드가 생기면 이 파일을 지우고 lib/data.ts 의 fetch 대상만 바꾸면 됩니다.
 */

/** 개발 중 핫 리로드로 모듈이 다시 평가돼도 유지되도록 globalThis에 붙인다 */
const globalForStore = globalThis as unknown as { staffiUpload?: AnalyzedStore | null };

/** 방금 업로드해 분석한 결과를 저장 (한 번에 한 매장) */
export function saveAnalysis(analysis: AnalyzedStore): void {
  globalForStore.staffiUpload = analysis;
}

/** 업로드한 분석 결과 — 없으면 null */
export function readAnalysis(): AnalyzedStore | null {
  return globalForStore.staffiUpload ?? null;
}

/** 기본 시연 데이터로 되돌린다 */
export function clearAnalysis(): void {
  globalForStore.staffiUpload = null;
}

/** 한 렌더 안에서는 같은 값을 보도록 묶어 준다 */
export const getUploadedAnalysis = cache(readAnalysis);
