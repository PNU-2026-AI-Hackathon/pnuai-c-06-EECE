import { Link } from "react-router-dom";

import { Header } from "../components/Layout";
import { WaitlistForm } from "../components/WaitlistForm";

/**
 * 요금 안내.
 *
 * **한동안 우리 원가를 화면에 그대로 공개했다.** 검사 한 번에 얼마가 드는지,
 * 데이터시트를 몇 번 읽었는지까지 서버에서 실시간으로 가져와 보여줬다.
 *
 * 그건 **팀 안에서 가격을 정하려고 만든 자료**였지 사용자가 볼 것이 아니었다.
 * 커피를 사면서 원두 원가표를 받는 것과 같다 — 정직해 보이지만 사는 사람에게는
 * 쓸모가 없고, 오히려 아직 파는 법을 못 정한 것처럼 읽힌다.
 *
 * 남긴 것은 사용자가 고를 때 필요한 것뿐이다 — **무엇을 얼마에 주는가.**
 */
export function PricingPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-4xl px-5 py-14 md:py-20">
        <p className="mb-3 text-[13px] font-bold tracking-tight text-brand-strong">요금</p>
        <h1 className="mb-4 text-[28px] font-extrabold leading-snug tracking-tight md:text-[38px]">
          검사는 계속 무료입니다
        </h1>
        <p className="mb-12 max-w-2xl text-[16px] leading-relaxed text-sub md:text-[17px]">
          회로도와 코드를 대조하는 검사는 횟수 제한 없이 무료입니다.
          결과를 오래 보관하거나 팀에서 쓰실 때만 요금을 받습니다.
        </p>

        {/* ── 요금제 ───────────────────────────────────────────── */}
        <h2 className="mb-7 text-[19px] font-extrabold tracking-tight md:text-[22px]">
          요금제
        </h2>

        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <Plan
            name="무료"
            price="0원"
            note="지금 쓰실 수 있습니다"
            lines={[
              "검사 무제한",
              "공개 부품 사실 DB 전부",
              "판정마다 근거와 출처",
              "결과 링크 공유와 JSON 내려받기",
            ]}
            limit="같은 주소에서 분당 20회 · 시간당 200회까지 올릴 수 있습니다."
            highlight
          />
          <Plan
            name="Pro"
            price="9,900원"
            unit="/ 월"
            note="개인 · 소규모"
            lines={[
              "무료의 모든 것",
              "결과 무기한 보관 · 비공개 링크",
              "아직 안 읽은 부품 데이터시트 읽기 요청",
              "규칙 발견 루프 — 내 보드에서 새 규칙 찾기",
            ]}
            waitlist="pro"
          />
          <Plan
            name="팀"
            price="39,000원"
            unit="/ 월"
            note="발주가 잦은 팀"
            lines={[
              "Pro의 모든 것",
              "CI 연동 — 회로도가 바뀐 PR에서 자동 검사",
              "사내 부품 사실 등록 (공개 DB와 분리)",
              "사내 규칙 추가",
            ]}
            waitlist="team"
          />
        </div>

        <div className="rounded-card border border-warn/25 bg-warn-weak p-6">
          <p className="mb-2 text-[15px] font-extrabold text-ink">
            Pro · 팀 플랜은 준비 중입니다.
          </p>
          <p className="text-[14px] leading-relaxed text-sub">
            출시하면 위에서 알림을 신청하신 분께 먼저 알려드립니다.
            그때까지 무료 플랜의 모든 기능을 제한 없이 쓰실 수 있습니다.
          </p>
        </div>

        <div className="mt-10 flex flex-wrap items-center gap-4 border-t border-line pt-8">
          <Link
            to="/check"
            className="rounded-block bg-brand-strong px-6 py-3.5 text-[15px] font-bold text-white shadow-brand transition hover:brightness-105"
          >
            무료로 검사해 보기
          </Link>
          <Link to="/privacy" className="text-[14px] font-bold text-sub hover:text-ink">
            데이터 처리 안내
          </Link>
        </div>
      </main>
    </div>
  );
}

function Plan({
  name,
  price,
  unit,
  note,
  lines,
  limit,
  highlight,
  waitlist,
}: {
  name: string;
  price: string;
  /** "/ 월" 처럼 가격 뒤에 붙는 단위. 무료 플랜에는 없다 */
  unit?: string;
  note: string;
  lines: string[];
  limit?: string;
  highlight?: boolean;
  /** 주면 카드 아래에 「출시 알림 받기」가 붙는다 */
  waitlist?: "pro" | "team";
}) {
  return (
    <section
      className={`flex flex-col rounded-card border p-6 ${
        highlight ? "border-brand/30 bg-surface shadow-card" : "border-line bg-surface"
      }`}
    >
      <p className="mb-1 text-[13px] font-bold text-sub">{name}</p>
      <p className="text-[26px] font-extrabold tracking-tight text-ink">
        {price}
        {unit && <span className="ml-1 text-[14px] font-bold text-mute">{unit}</span>}
      </p>
      <p className="mb-5 text-[13px] text-mute">{note}</p>
      <ul className="flex-1 space-y-2.5">
        {lines.map((line) => (
          <li key={line} className="flex gap-2 text-[14px] leading-relaxed text-sub">
            <span aria-hidden className={highlight ? "text-brand" : "text-mute"}>
              ·
            </span>
            <span>{line}</span>
          </li>
        ))}
      </ul>
      {limit && (
        <p className="mt-5 border-t border-line pt-4 text-[12.5px] leading-relaxed text-mute">
          {limit}
        </p>
      )}
      {waitlist && <WaitlistForm plan={waitlist} planLabel={name} />}
    </section>
  );
}
