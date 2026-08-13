"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "@/components/layout/nav-items";
import { cn } from "@/lib/utils";

/** 현재 경로가 해당 메뉴에 해당하는지 */
function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

/**
 * 데스크톱 사이드바 (좌측 고정) + 모바일 하단 탭바.
 * 주 사용 환경은 데스크톱이지만 모바일에서도 같은 메뉴에 닿을 수 있어야 한다.
 */
export function Sidebar() {
  const pathname = usePathname();

  return (
    <>
      <aside className="hidden w-64 shrink-0 border-r bg-card lg:block">
        <div className="sticky top-0 flex h-screen flex-col">
          <div className="border-b px-6 py-6">
            <p className="text-xl font-bold tracking-tight">STAFFI</p>
            <p className="mt-1 text-sm text-muted-foreground">Your AI Staff</p>
          </div>

          <nav aria-label="주요 메뉴" className="flex-1 space-y-1 p-3">
            {NAV_ITEMS.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-start gap-3 rounded-lg px-3 py-3 transition-colors",
                    active
                      ? "bg-brand-soft font-bold text-accent-foreground"
                      : "font-medium text-foreground hover:bg-secondary"
                  )}
                >
                  <item.icon aria-hidden className="mt-0.5 size-5 shrink-0" strokeWidth={active ? 2.5 : 2} />
                  <span className="min-w-0">
                    <span className="block text-base leading-tight">{item.label}</span>
                    <span className="mt-0.5 block text-sm font-normal leading-tight text-muted-foreground">
                      {item.description}
                    </span>
                  </span>
                </Link>
              );
            })}
          </nav>

          <div className="border-t px-6 py-4 text-sm text-muted-foreground">
            부산대 앞 상권 파일럿
          </div>
        </div>
      </aside>

      <nav
        aria-label="주요 메뉴"
        className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-6 border-t bg-card lg:hidden"
      >
        {NAV_ITEMS.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex flex-col items-center gap-1 py-2.5 text-xs",
                active ? "font-bold text-primary" : "text-muted-foreground"
              )}
            >
              <item.icon aria-hidden className="size-5" strokeWidth={active ? 2.5 : 2} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
