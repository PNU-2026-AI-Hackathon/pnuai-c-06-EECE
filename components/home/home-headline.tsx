import type { DataOrigin, Forecast, Store } from "@/types";

import { DataOriginBadge } from "@/components/common/data-origin-badge";
import type { SemesterRibbon } from "@/lib/semester";

/** 업종 코드를 한글로 */
const CATEGORY_LABEL = { cafe: "카페", restaurant: "식당", pub: "주점" } as const;

/**
 * 홈 첫 화면의 한 문장.
 * 라벨과 숫자를 늘어놓는 대신 결론부터 말한다. 첫 줄만 읽어도 이번 주가 어떤 주인지 안다.
 */
export function HomeHeadline({
  store,
  forecast,
  ribbon,
  origin,
}: {
  store: Store;
  forecast: Forecast;
  ribbon: SemesterRibbon;
  /** 이 화면 숫자의 출처 — real이면 배지가 붙지 않는다 */
  origin: DataOrigin;
}) {
  const range = forecast.expectedRange;
  const eventName = ribbon.next?.event.name;
  const down = range !== null && range.high < 0;

  return (
    <header className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-base text-muted-foreground">
          {store.name} · {CATEGORY_LABEL[store.category]} · {ribbon.label} {ribbon.weekNumber}주차
        </p>
        <DataOriginBadge origin={origin} />
      </div>

      <h1 className="text-headline">
        {eventName ? (
          <>
            이번 주는 <span className="font-bold">{eventName}</span>예요.
            <br />
          </>
        ) : (
          <>이번 주 매장은 이렇게 볼 수 있어요.<br /></>
        )}
        {range ? (
          <>
            매출이{" "}
            <span className={down ? "font-bold text-down" : "font-bold text-up"}>
              {Math.abs(range.high)}~{Math.abs(range.low)}% {down ? "줄어들" : "늘어날"}
            </span>{" "}
            것 같아요.
          </>
        ) : (
          <>아직 예측을 만들 수는 없어요.</>
        )}
      </h1>
    </header>
  );
}
