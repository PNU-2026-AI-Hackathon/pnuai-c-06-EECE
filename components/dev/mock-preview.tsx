"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { mockForecastConfident, mockForecastInsufficient, mockForecastLimited } from "@/mocks";

import { MockAnalysisPanel } from "./mock-analysis-panel";
import { MockForecastPanel } from "./mock-forecast-panel";
import { MockMissedPanel } from "./mock-missed-panel";
import { MockRawPanel } from "./mock-raw-panel";
import { MockValidationPanel } from "./mock-validation-panel";

/**
 * 개발 전용 목 데이터 프리뷰.
 * 실제 사장님 화면이 아니라 데이터 확인용이므로, 본 화면 개발이 끝나면 app/dev와 함께 삭제한다.
 */
export function MockPreview() {
  return (
    <Tabs defaultValue="analysis" className="w-full">
      <TabsList className="flex h-auto flex-wrap justify-start">
        <TabsTrigger value="analysis">정상 분석</TabsTrigger>
        <TabsTrigger value="confident">예측 · 충분</TabsTrigger>
        <TabsTrigger value="limited">예측 · 제한적</TabsTrigger>
        <TabsTrigger value="insufficient">예측 · 불가</TabsTrigger>
        <TabsTrigger value="missed">놓친 기회</TabsTrigger>
        <TabsTrigger value="validation">예측 검증</TabsTrigger>
        <TabsTrigger value="raw">원본 · 정규화</TabsTrigger>
      </TabsList>

      <TabsContent value="analysis" className="mt-4">
        <MockAnalysisPanel />
      </TabsContent>
      <TabsContent value="confident" className="mt-4">
        <MockForecastPanel forecast={mockForecastConfident} />
      </TabsContent>
      <TabsContent value="limited" className="mt-4">
        <MockForecastPanel forecast={mockForecastLimited} />
      </TabsContent>
      <TabsContent value="insufficient" className="mt-4">
        <MockForecastPanel forecast={mockForecastInsufficient} />
      </TabsContent>
      <TabsContent value="missed" className="mt-4">
        <MockMissedPanel />
      </TabsContent>
      <TabsContent value="validation" className="mt-4">
        <MockValidationPanel />
      </TabsContent>
      <TabsContent value="raw" className="mt-4">
        <MockRawPanel />
      </TabsContent>
    </Tabs>
  );
}
