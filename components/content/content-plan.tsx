import { Clock, Hash, Clapperboard, Lightbulb } from "lucide-react";

import type { ContentGeneration } from "@/types";

import { DataOriginBadge } from "@/components/common/data-origin-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDateTimeShort } from "@/lib/format";

/**
 * 홍보 콘텐츠 한 벌 — 왜 지금인지, 언제 올릴지, 무엇을 찍을지.
 *
 * 사장님이 이 화면만 보고 촬영과 게시를 끝낼 수 있어야 하므로
 * 문구를 그대로 옮겨 적을 수 있는 형태로 보여준다.
 */
export function ContentPlan({ content }: { content: ContentGeneration }) {
  const totalSec = content.scenes.reduce((s, scene) => s + scene.durationSec, 0);

  return (
    <div className="space-y-6">
      <Card className="shadow-none">
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-xl">이 콘텐츠를 지금 만드는 이유</CardTitle>
            <DataOriginBadge origin={content.origin} />
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-base leading-relaxed">{content.situationSummary}</p>
        </CardContent>
      </Card>

      <Card className="shadow-none">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-xl">
            <Clock aria-hidden className="size-5" />
            언제 올리면 좋을까요
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-3xl font-bold">{formatDateTimeShort(content.recommendedPostAt)}</p>
          <p className="text-base leading-relaxed text-muted-foreground">
            {content.recommendedPostReason}
          </p>
        </CardContent>
      </Card>

      <Card className="shadow-none">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-xl">
            <Clapperboard aria-hidden className="size-5" />
            릴스 대본
          </CardTitle>
          <p className="text-base text-muted-foreground">
            {content.scenes.length}컷 · 전체 {totalSec}초
          </p>
        </CardHeader>
        <CardContent>
          <ol className="space-y-5">
            {content.scenes.map((scene) => (
              <li key={scene.order} className="flex gap-4">
                <div
                  aria-hidden
                  className="flex size-9 shrink-0 items-center justify-center rounded-full bg-secondary text-base font-bold"
                >
                  {scene.order}
                </div>
                <div className="min-w-0 flex-1 space-y-1.5">
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <p className="text-lg font-bold leading-snug">{scene.caption}</p>
                    <span className="tnum text-base text-muted-foreground">{scene.durationSec}초</span>
                  </div>
                  <p className="text-base leading-relaxed">
                    <span className="font-medium text-muted-foreground">찍을 것: </span>
                    {scene.visual}
                  </p>
                  {scene.tip && (
                    <p className="flex gap-2 rounded-md bg-secondary/60 p-3 text-base leading-relaxed">
                      <Lightbulb aria-hidden className="mt-0.5 size-5 shrink-0" />
                      <span>
                        <span className="sr-only">촬영 팁: </span>
                        {scene.tip}
                      </span>
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      <Card className="shadow-none">
        <CardHeader className="pb-2">
          <CardTitle className="text-xl">게시글 문구</CardTitle>
          <p className="text-base text-muted-foreground">그대로 붙여 넣으셔도 됩니다</p>
        </CardHeader>
        <CardContent className="space-y-5">
          <p className="whitespace-pre-line rounded-lg border bg-secondary/40 p-4 text-base leading-relaxed">
            {content.caption}
          </p>

          <div className="space-y-2">
            <p className="flex items-center gap-2 text-base font-semibold text-muted-foreground">
              <Hash aria-hidden className="size-4" />
              해시태그 {content.hashtags.length}개
            </p>
            <ul className="flex flex-wrap gap-2">
              {content.hashtags.map((tag) => (
                <li key={tag}>
                  <Badge variant="outline" className="text-base font-medium">
                    {tag}
                  </Badge>
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
