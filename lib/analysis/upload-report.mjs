/**
 * 업로드한 파일이 무엇을 할 수 있고 무엇을 못 하는지 정리한다.
 *
 * 사장님이 파일을 올린 직후 가장 먼저 보는 화면이고,
 * 여기서 "안 되는 것"을 정직하게 말해 두어야 뒤 화면의 빈칸이 설명된다.
 * 판단 근거는 파일에 실제로 들어 있는 것뿐이다 — 있을 법한 것을 가정하지 않는다.
 */

/** 이 파일로 무엇이 되고 무엇이 안 되는지 — 파일에 실제로 들어 있는 것에서만 판단한다 */
export function buildCapabilities({ hasTime, hasMenu, weeksCovered }) {
  return [
    { kind: "daily_sales", label: "일별 매출", available: true, missingReason: null },
    {
      kind: "weekday_pattern",
      label: "요일별 패턴",
      available: weeksCovered >= 2,
      missingReason: weeksCovered >= 2 ? null : "완전한 주가 2주 이상 있어야 요일 패턴을 볼 수 있습니다.",
    },
    {
      kind: "menu_analysis",
      label: "메뉴별 분석",
      available: hasMenu,
      missingReason: hasMenu ? null : "메뉴 정보가 없어 메뉴별 분석은 할 수 없습니다.",
    },
    {
      kind: "hourly_pattern",
      label: "시간대별 매출",
      available: hasTime,
      missingReason: hasTime ? null : "결제 시각이 없어 시간대별 매출은 만들 수 없습니다.",
    },
    {
      kind: "academic_event",
      label: "학사일정 비교",
      available: weeksCovered >= 8,
      missingReason:
        weeksCovered >= 8
          ? null
          : `학사일정과 비교하려면 8주 이상이 필요합니다. 지금은 ${weeksCovered}주입니다.`,
    },
    {
      kind: "early_sales_end",
      label: "판매 조기 종료 탐지",
      available: hasTime && hasMenu,
      missingReason:
        hasTime && hasMenu
          ? null
          : "결제 시각과 메뉴가 함께 있어야 판매가 일찍 끝났는지 알 수 있습니다.",
    },
  ];
}

/**
 * 이 데이터로는 만들 수 없는 것들 — 화면에서 그대로 사장님께 알린다.
 * 경고 코드를 함께 붙여 백엔드가 같은 분류를 쓸 수 있게 한다.
 */
export function buildLimitations({ hasTime, hasMenu, maxRelError, shape }) {
  const limitations = [];
  if (!hasTime) {
    limitations.push({
      code: "MISSING_VALUE",
      message: "결제 시각이 없어 시간대별 매출을 만들 수 없습니다.",
    });
    limitations.push({
      code: "MISSING_VALUE",
      message: "개별 결제 내역이 아닌 일별 집계라 판매가 일찍 끝났는지 판단할 수 없습니다.",
    });
  }
  if (!hasMenu) {
    limitations.push({
      code: "UNKNOWN_MENU",
      message: "메뉴 정보가 없어 메뉴별 분석을 할 수 없습니다.",
    });
  }
  if (hasMenu && shape === "daily") {
    limitations.push({
      code: "UNKNOWN_MENU",
      message: `메뉴 단가는 매출과 판매 수량으로 역산한 값입니다. 역산 오차는 ${(
        maxRelError * 100
      ).toFixed(2)}%입니다.`,
    });
  }
  return limitations;
}

export function buildUploadResult({
  rows,
  prices,
  maxRelError,
  menus,
  weeksCovered,
  today,
  skipped,
  shape,
  hasTime,
  hasMenu,
  store,
  fileName,
  processedRows,
}) {
  const sum = (xs) => xs.reduce((s, x) => s + x, 0);
  const menuNormalizations = menus.map((menu) => ({
    rawName: `${menu}_판매수량`,
    normalizedName: menu,
    confidence: 1,
    occurrences: sum(rows.map((r) => r.quantities[menu])),
  }));

  return {
    id: `upload_${store.id}`,
    storeId: store.id,
    fileName,
    uploadedAt: `${today}T21:40:00`,
    // 사장님이 세는 단위는 "파일에 적힌 줄"이다. 집계 후 날짜 수가 아니라 읽어들인 기록 수를 보여준다.
    processedRows: processedRows ?? rows.length,
    skippedRows: skipped.badDate + skipped.missingRevenue,
    period: { start: rows[0].date, end: rows[rows.length - 1].date },
    recognizedMenuCount: Object.keys(prices).length,
    menuNormalizations,
    warnings: buildLimitations({ hasTime, hasMenu, maxRelError, shape }).map(({ code, message }) => ({
      code,
      level: "warning",
      message,
      affectedRows: 0,
    })),
    capabilities: buildCapabilities({ hasTime, hasMenu, weeksCovered }),
    weeksCovered,
    origin: "computed",
  };
}
