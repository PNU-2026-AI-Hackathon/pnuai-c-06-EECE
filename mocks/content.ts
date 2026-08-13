import type { ContentGeneration } from "@/types";
import type { Mock } from "./types";

/**
 * 중간고사 주를 앞두고 만든 릴스 콘텐츠.
 * 예측(+13%)과 놓친 기회(목요일 소금빵 품절)를 그대로 홍보 소재로 옮긴 결과다.
 */
export const mockContentGeneration: Mock<ContentGeneration> = {
  id: "content_20261019_midterm",
  storeId: "store_pnu_001",
  situationSummary:
    "다음 주가 중간고사(10/19~24)입니다. 오후 2~6시 카페 체류 손님이 늘어날 것으로 보이고, 목요일 소금빵은 3주 연속 오후에 품절됐습니다. 시험 기간 장시간 공부 손님을 겨냥한 콘텐츠가 맞습니다.",
  scenes: [
    {
      order: 1,
      durationSec: 3,
      visual: "창가 자리에 노트북과 필기 노트를 펼친 손님의 뒷모습, 창밖으로 캠퍼스가 보이게",
      caption: "시험기간 D-1",
      tip: "얼굴은 안 나오게 어깨 위로만 잡으면 촬영 동의가 쉬워집니다.",
    },
    {
      order: 2,
      durationSec: 4,
      visual: "아이스 아메리카노에 얼음이 떨어지는 순간 클로즈업",
      caption: "3시간째 앉아 있어도 괜찮아요",
    },
    {
      order: 3,
      durationSec: 4,
      visual: "오븐에서 갓 나온 소금빵을 트레이에 올리는 장면",
      caption: "소금빵은 오후 4시면 없어져요",
      tip: "김이 보이도록 오븐에서 꺼낸 직후 10초 안에 찍으세요.",
    },
    {
      order: 4,
      durationSec: 3,
      visual: "콘센트가 있는 좌석과 조용한 매장 전경을 천천히 팬",
      caption: "콘센트 자리 12석 · 22시까지",
    },
    {
      order: 5,
      durationSec: 3,
      visual: "매장 간판과 영업시간이 함께 보이는 컷",
      caption: "부산대 정문 3분 · 카페 온담",
    },
  ],
  caption:
    "중간고사 기간에도 22시까지 엽니다.\n콘센트 자리 12석, 아이스 아메리카노 4,000원.\n소금빵은 매일 오후에 떨어지니 일찍 오세요 🥐\n부산대 정문에서 걸어서 3분.",
  hashtags: [
    "#부산대카페",
    "#장전동카페",
    "#부산대맛집",
    "#중간고사",
    "#부산대공부카페",
    "#소금빵",
    "#카공카페",
    "#금정구카페",
  ],
  recommendedPostAt: "2026-10-18T20:00:00",
  recommendedPostReason:
    "일요일 저녁 8~9시에 이 계정 팔로워의 접속이 가장 많고, 시험 시작 전날이라 다음 날 갈 곳을 정하는 시점입니다.",
  generatedAt: "2026-10-18T14:22:10",
  origin: "sample",
  isMockData: true,
};

/** 데이터가 부족할 때의 콘텐츠 — 예측 없이 학사일정만 근거로 삼는다 */
export const mockContentGenerationBasic: Mock<ContentGeneration> = {
  id: "content_20261019_basic",
  storeId: "store_pnu_002",
  situationSummary:
    "매출 데이터가 3주치뿐이라 수요 예측은 못 하지만, 다음 주가 중간고사라는 학사일정은 확실합니다. 예측 없이 일정만 근거로 만든 콘텐츠입니다.",
  scenes: [
    {
      order: 1,
      durationSec: 4,
      visual: "매장 외관과 오픈 안내문",
      caption: "부산대 앞에 새로 열었습니다",
    },
    {
      order: 2,
      durationSec: 4,
      visual: "드립 커피를 내리는 장면",
      caption: "시험기간, 조용한 자리 있습니다",
    },
    {
      order: 3,
      durationSec: 3,
      visual: "메뉴판과 가격이 보이는 컷",
      caption: "아메리카노 3,800원",
    },
  ],
  caption: "9월에 문 연 브루잉랩입니다.\n중간고사 기간 동안 21시까지 엽니다.\n부산대 후문 도보 5분.",
  hashtags: ["#부산대카페", "#장전동", "#신규오픈", "#중간고사", "#부산대후문"],
  recommendedPostAt: "2026-10-18T19:30:00",
  recommendedPostReason: "게시 시각은 일반적인 지역 카페 계정 기준이며, 이 매장 데이터로 검증된 값은 아닙니다.",
  generatedAt: "2026-10-18T15:05:41",
  origin: "sample",
  isMockData: true,
};
