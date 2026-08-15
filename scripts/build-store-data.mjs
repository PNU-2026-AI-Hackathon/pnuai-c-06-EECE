/**
 * 매출 CSV → mocks/generated/store-data.json
 *
 * 업로드 전에 보여줄 기본 시연 데이터를 만든다.
 * 계산은 전부 lib/analysis/analyze.mjs 가 한다 — 업로드 API와 완전히 같은 코드다.
 * 여기서는 파일을 읽고 쓰는 일만 한다.
 *
 * 실행: node scripts/build-store-data.mjs [--store=data/store.json] [--file=매출.csv] [--today=YYYY-MM-DD]
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { analyzeSales } from "../lib/analysis/analyze.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT_PATH = path.join(ROOT, "mocks/generated/store-data.json");

/** --key=value 형태의 실행 인자 */
function arg(name, fallback) {
  const hit = process.argv.slice(2).find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3) : fallback;
}

function main() {
  const configPath = path.resolve(ROOT, arg("store", "data/store.json"));
  const config = JSON.parse(fs.readFileSync(configPath, "utf8"));

  const salesPath = path.resolve(ROOT, arg("file", config.salesFile));
  const calendarPath = path.resolve(ROOT, config.academicCalendar);

  const result = analyzeSales({
    csvText: fs.readFileSync(salesPath, "utf8"),
    fileName: path.basename(salesPath),
    calendar: JSON.parse(fs.readFileSync(calendarPath, "utf8")),
    store: { id: config.id, name: config.name, category: config.category },
    today: arg("today", config.today) || null,
  });

  if (!result.ok) {
    console.error(`분석할 수 없습니다: ${result.reason}`);
    process.exit(1);
  }

  const output = {
    meta: {
      generatedFrom: path.relative(ROOT, salesPath),
      academicCalendar: path.relative(ROOT, calendarPath),
      generatedAt: new Date().toISOString(),
      demoToday: result.meta.asOf,
      estimatedPrices: result.meta.estimatedPrices,
      priceEstimationMaxError: result.meta.priceEstimationMaxError,
      weeksAvailable: result.meta.weeksAvailable,
      note: "이 파일은 scripts/build-store-data.mjs 가 CSV에서 생성합니다. 직접 수정하지 마세요.",
    },
    store: result.store,
    weeklyAnalysis: result.weeklyAnalysis,
    forecast: result.forecast,
    verification: result.verification,
    upload: result.upload,
    earlySalesEnds: result.earlySalesEnds,
    dataLimitations: result.dataLimitations,
    dailySeries: result.dailySeries,
  };

  fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });
  fs.writeFileSync(OUT_PATH, `${JSON.stringify(output, null, 2)}\n`);

  const { meta, weeklyAnalysis, forecast, verification } = output;
  console.log(`생성 완료: ${path.relative(ROOT, OUT_PATH)}`);
  console.log(`  매장: ${config.name} (${meta.generatedFrom}, ${result.meta.shape})`);
  console.log(`  기준 시점: ${meta.demoToday}${config.today ? "" : " (파일의 마지막 날짜)"}`);
  console.log(`  인식한 메뉴: ${Object.keys(meta.estimatedPrices).join(", ") || "없음"}`);
  if (result.meta.uncoveredDays > 0) {
    console.log(`  ⚠ 학사일정이 없는 날짜 ${result.meta.uncoveredDays}일 — 캘린더 확인 필요`);
  }
  console.log(`  단가 역산 최대 오차: ${(meta.priceEstimationMaxError * 100).toFixed(4)}%`);
  console.log(
    `  분석 주: ${weeklyAnalysis.period.start} ~ ${weeklyAnalysis.period.end} (${weeklyAnalysis.totalRevenue.toLocaleString()}원)`
  );
  console.log(
    `  예측 주: ${forecast.targetWeek.start} ~ ${forecast.targetWeek.end} (${forecast.expectedChangeRate}%)`
  );
  console.log(
    `  검증: 예측 ${verification.predictedChangeRate}% vs 실제 ${verification.actualChangeRate}%`
  );
  console.log(`  조기 종료 후보: ${result.earlySalesEnds.length}건`);
}

main();
