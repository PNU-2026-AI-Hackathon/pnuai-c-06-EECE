/**
 * 일별 집계 CSV → 결제 내역형 샘플 CSV
 *
 * ⚠ 결과물은 **샘플**이다. 실제 결제 기록이 아니다.
 *   일별 합계는 원본과 정확히 일치하지만, 결제 시각은 우리가 지어낸 값이다.
 *   결제 내역형 파일이 아직 없어서 파이프라인을 시험할 수 없기 때문에 만든다.
 *   시연이나 분석에 쓰지 말 것 — data/store.json 에 연결하지 않는다.
 *
 * 실행: node scripts/make-transaction-sample.mjs [--out=data/samples/파일.csv]
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { estimateMenuPrices, parseSales } from "../lib/analysis/csv-model.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function arg(name, fallback) {
  const hit = process.argv.slice(2).find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3) : fallback;
}

const IN_PATH = path.resolve(ROOT, arg("in", "data/pub-sales-pnu-2025.csv"));
const OUT_PATH = path.resolve(ROOT, arg("out", "data/samples/pub-transactions-sample.csv"));

/** 같은 결과가 나오도록 고정 시드 난수 */
function makeRandom(seed) {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
}

/** 17:00~23:50 사이, 21시 30분쯤에 몰리도록 */
function pickMinute(random) {
  const peak = 21 * 60 + 30;
  const draw = (random() + random() + random()) / 3; // 가운데로 모이게
  const minute = Math.round(peak + (draw - 0.5) * 380);
  return Math.min(Math.max(minute, 17 * 60), 23 * 60 + 50);
}

function main() {
  const parsed = parseSales(fs.readFileSync(IN_PATH, "utf8"));
  if (parsed.menus.length === 0) throw new Error("메뉴 컬럼이 없는 파일이라 결제 단위로 펼칠 수 없습니다.");

  const { prices } = estimateMenuPrices(parsed.rows, parsed.menus);
  const random = makeRandom(20251019);
  const lines = ["날짜,결제시각,메뉴명,수량,결제금액"];
  let count = 0;

  // 일부러 심어 두는 패턴: 마지막 6주 금요일의 계란찜은 20:30 이후로 팔리지 않는다.
  // 탐지가 실제로 걸리는지 확인하기 위한 것이고, 이 사실은 여기 적어 둔다.
  const injectMenu = parsed.menus.includes("계란찜") ? "계란찜" : parsed.menus[parsed.menus.length - 1];
  const lastDate = parsed.rows[parsed.rows.length - 1].date;
  const injectFrom = new Date(`${lastDate}T00:00:00Z`);
  injectFrom.setUTCDate(injectFrom.getUTCDate() - 42);
  const injectFromDate = injectFrom.toISOString().slice(0, 10);

  for (const row of parsed.rows) {
    const sales = [];
    for (const menu of parsed.menus) {
      const injected = menu === injectMenu && row.weekday === 5 && row.date >= injectFromDate;
      for (let i = 0; i < row.quantities[menu]; i++) {
        const minute = injected ? Math.min(pickMinute(random), 20 * 60 + 30) : pickMinute(random);
        sales.push({ minute, menu });
      }
    }
    sales.sort((a, b) => a.minute - b.minute);
    for (const sale of sales) {
      const clock = `${String(Math.floor(sale.minute / 60)).padStart(2, "0")}:${String(
        sale.minute % 60
      ).padStart(2, "0")}`;
      lines.push(`${row.date},${clock},${sale.menu},1,${prices[sale.menu]}`);
      count += 1;
    }
  }

  fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });
  fs.writeFileSync(OUT_PATH, `${lines.join("\n")}\n`);

  console.log(`샘플 생성: ${path.relative(ROOT, OUT_PATH)}`);
  console.log(`  결제 ${count.toLocaleString()}건 (${parsed.rows.length}일)`);
  console.log(`  ⚠ 결제 시각은 지어낸 값입니다. 일별 합계만 원본과 일치합니다.`);
  console.log(`  심어 둔 패턴: ${injectFromDate} 이후 금요일 ${injectMenu} 20:30 마감`);
}

main();
