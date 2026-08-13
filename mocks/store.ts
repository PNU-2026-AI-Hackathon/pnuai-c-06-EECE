import type { Store } from "@/types";
import type { Mock } from "./types";

/** 시연 기준 매장 — 부산대 정문 앞 소규모 카페 (2024년 개업, 데이터 충분) */
export const mockStore: Mock<Store> = {
  id: "store_pnu_001",
  name: "카페 온담",
  category: "cafe",
  openedAt: "2024-03-11",
  isMockData: true,
};

/** 데이터 부족 시나리오용 매장 — 2026년 9월 개업, 매출 이력 3주치뿐 */
export const mockStoreNew: Mock<Store> = {
  id: "store_pnu_002",
  name: "브루잉랩 장전",
  category: "cafe",
  openedAt: "2026-09-21",
  isMockData: true,
};
