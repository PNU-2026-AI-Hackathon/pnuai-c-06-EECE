import type { LucideIcon } from "lucide-react";
import { BarChart3, Home, Megaphone, Settings, TrendingUp } from "lucide-react";

/** 사이드바 메뉴 한 개 */
export interface NavItem {
  /** 이동 경로 */
  href: string;
  /** 메뉴 이름 */
  label: string;
  /** 메뉴 아이콘 */
  icon: LucideIcon;
  /** 메뉴 아래 한 줄 설명 (사이드바 확장 시 표시) */
  description: string;
}

/** 사이드바 메뉴 — 사장님이 보는 순서대로 */
export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "홈", icon: Home, description: "오늘 봐야 할 것만" },
  { href: "/weekly", label: "주간 리포트", icon: BarChart3, description: "지난주 매출 정리" },
  { href: "/forecast", label: "수요 예측", icon: TrendingUp, description: "다음 주 어떻게 될까" },
  { href: "/content", label: "홍보 콘텐츠", icon: Megaphone, description: "릴스·게시글 만들기" },
  { href: "/settings", label: "설정", icon: Settings, description: "매장 정보와 파일" },
];
