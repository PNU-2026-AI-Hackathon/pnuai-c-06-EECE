import type { MenuSales } from "@/types";

import { MockDataBadge } from "@/components/common/mock-data-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatWon } from "@/lib/format";

/** 메뉴별 판매 표. 비중은 숫자와 막대를 함께 보여준다 */
export function MenuSalesTable({
  menus,
  isMockData = false,
}: {
  menus: MenuSales[];
  isMockData?: boolean;
}) {
  const max = Math.max(...menus.map((m) => m.share), 1);

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="text-xl">많이 팔린 메뉴</CardTitle>
          {isMockData && <MockDataBadge />}
        </div>
        <p className="text-base text-muted-foreground">수량 기준 상위 {menus.length}개</p>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-base">메뉴</TableHead>
              <TableHead className="text-right text-base">수량</TableHead>
              <TableHead className="text-right text-base">매출</TableHead>
              <TableHead className="text-base">비중</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {menus.map((m) => (
              <TableRow key={m.menuName}>
                <TableCell className="text-base font-semibold">{m.menuName}</TableCell>
                <TableCell className="tnum text-right text-base">{m.quantity}개</TableCell>
                <TableCell className="tnum text-right text-base">{formatWon(m.revenue)}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <div aria-hidden className="h-2.5 w-24 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${Math.max((m.share / max) * 100, 4)}%` }}
                      />
                    </div>
                    <span className="tnum text-base font-semibold">{m.share.toFixed(1)}%</span>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
