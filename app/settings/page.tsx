import { DataFreshnessNotice } from "@/components/agent/data-freshness-notice";
import { PageHeader } from "@/components/layout/page-header";
import { CsvUploadZone } from "@/components/upload/csv-upload-zone";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getDataFreshness,
  getLatestUpload,
  getStore,
  isViewingUpload,
  parseScenario,
} from "@/lib/data";
import { formatPeriod } from "@/lib/format";

/** 업종 코드를 한글 라벨로 */
const CATEGORY_LABEL = { cafe: "카페", restaurant: "식당", pub: "주점" } as const;

/** 업로드한 파일이 서버 메모리에 있으므로 이 화면은 매번 새로 그린다 */
export const dynamic = "force-dynamic";

/** 설정 — 매장 정보와 매출 파일 관리 */
export default async function SettingsPage({ searchParams }: { searchParams: { scenario?: string } }) {
  const scenario = parseScenario(searchParams.scenario);
  const [store, lastUpload, freshness, viewingUpload] = await Promise.all([
    getStore(scenario),
    getLatestUpload(scenario),
    getDataFreshness(scenario),
    isViewingUpload(),
  ]);

  return (
    <>
      <PageHeader
        title="설정"
        description="매장 정보와 올려주신 매출 파일을 관리합니다."
      />

      <DataFreshnessNotice freshness={freshness} />

      <section className="space-y-4" aria-label="매출 파일 올리기">
        <h2 className="text-2xl font-bold">매출 파일 올리기</h2>
        <CsvUploadZone viewingUpload={viewingUpload} />
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="text-xl">매장 정보</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="divide-y">
              <div className="flex justify-between py-3">
                <dt className="text-base text-muted-foreground">상호</dt>
                <dd className="text-base font-semibold">{store.name}</dd>
              </div>
              <div className="flex justify-between py-3">
                <dt className="text-base text-muted-foreground">업종</dt>
                <dd className="text-base font-semibold">{CATEGORY_LABEL[store.category]}</dd>
              </div>
              <div className="flex justify-between py-3">
                <dt className="text-base text-muted-foreground">개업일</dt>
                <dd className="tnum text-base font-semibold">{store.openedAt.replaceAll("-", ".")}</dd>
              </div>
              <div className="flex justify-between py-3">
                <dt className="text-base text-muted-foreground">기준 대학</dt>
                <dd className="text-base font-semibold">부산대학교</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card className="shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="text-xl">지금까지 올린 파일</CardTitle>
          </CardHeader>
          <CardContent>
            {lastUpload ? (
              <dl className="divide-y">
                <div className="flex justify-between gap-4 py-3">
                  <dt className="text-base text-muted-foreground">파일</dt>
                  <dd className="min-w-0 truncate text-base font-semibold">{lastUpload.fileName}</dd>
                </div>
                <div className="flex justify-between py-3">
                  <dt className="text-base text-muted-foreground">기간</dt>
                  <dd className="tnum text-base font-semibold">
                    {formatPeriod(lastUpload.period.start, lastUpload.period.end)}
                  </dd>
                </div>
                <div className="flex justify-between py-3">
                  <dt className="text-base text-muted-foreground">읽은 기록</dt>
                  <dd className="tnum text-base font-semibold">
                    {lastUpload.processedRows.toLocaleString("ko-KR")}건
                  </dd>
                </div>
                <div className="flex justify-between py-3">
                  <dt className="text-base text-muted-foreground">메뉴</dt>
                  <dd className="tnum text-base font-semibold">{lastUpload.recognizedMenuCount}개</dd>
                </div>
              </dl>
            ) : (
              <p className="text-base text-muted-foreground">아직 올려주신 파일이 없습니다.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
