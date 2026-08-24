import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Header } from "../components/Layout";
import { fetchUsage, type Usage } from "../lib/api";

/**
 * 요금 안내.
 *
 * **아직 아무에게도 청구하지 않는다.** 결제도 회원가입도 없다. 그러니 이 화면이
 * 하는 일은 파는 게 아니라 **원가를 공개하는 것**이다.
 *
 * 이 서비스의 원가는 직관과 다르게 생겼다. 검사는 순수 함수라 사실상 공짜이고,
 * 돈이 드는 것은 데이터시트를 읽는 일 하나뿐이며, 그 값은 부품마다 딱 한 번 든다.
 * 그래서 "많이 쓰면 비싸지는" 구조가 아니다 — 그 사실을 숨기고 사용량 요금제를
 * 흉내 내면 우리가 스스로를 속이게 된다.
 *
 * 숫자는 전부 `/api/v1/usage` 에서 가져온다. **손으로 적지 않는다.**
 */
export function PricingPage() {
  const [usage, setUsage] = useState<Usage | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchUsage().then((got) => {
      if (!alive) return;
      setUsage(got);
      setLoaded(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-4xl px-5 py-14 md:py-20">
        <p className="mb-3 text-[13px] font-bold tracking-tight text-brand-strong">요금</p>
        <h1 className="mb-4 text-[28px] font-extrabold leading-snug tracking-tight md:text-[38px]">
          검사는 계속 무료입니다
        </h1>
        <p className="mb-12 max-w-2xl text-[16px] leading-relaxed text-sub md:text-[17px]">
          그럴듯하게 들리려고 하는 말이 아니라, 원가가 실제로 그렇게 생겼습니다. 아래에 저희 원가를
          그대로 적었습니다.
        </p>

        {/* ── 원가 ─────────────────────────────────────────────── */}
        <section className="mb-14 rounded-card border border-line bg-surface p-6 shadow-card md:p-8">
          <h2 className="mb-5 text-[19px] font-extrabold tracking-tight md:text-[22px]">
            우리 원가가 어디서 나는가
          </h2>

          <Cost
            head="검사 한 번 — 거의 0원"
            body="규칙은 네트워크도 AI도 쓰지 않는 순수 함수입니다. 회로도와 펌웨어를 읽어 판정하는 데 걸리는 시간은 밀리초 단위이고, 드는 것은 서버 CPU뿐입니다."
          />
          <Cost
            head="부품 데이터시트 한 번 읽기 — 여기서만 돈이 듭니다"
            body="새 부품의 데이터시트에서 전기적 사실을 뽑을 때만 외부 AI 모델을 부릅니다. 부품 하나에 호출 한 번입니다."
          />
          <Cost
            head="그리고 그 값은 부품마다 딱 한 번 듭니다"
            tone="key"
            body="한 번 읽어 검증까지 마친 사실은 그 뒤로 모든 사용자, 모든 검사가 그대로 씁니다. 그래서 검사가 늘어도 비용은 늘지 않고, 새로운 부품 종류가 나올 때만 늘어납니다."
          />

          <div className="mt-7 rounded-block border border-line bg-surface-2 p-5">
            <p className="mb-4 text-[13px] font-bold text-sub">지금 이 서버의 실제 숫자</p>
            {!loaded ? (
              <p className="text-[14px] text-mute">불러오는 중…</p>
            ) : usage ? (
              <>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-5 md:grid-cols-4">
                  <Stat label="읽어 둔 부품" value={usage.parts} unit="개" />
                  <Stat label="검증된 사실" value={usage.facts} unit="개" />
                  <Stat label="처리한 검사" value={usage.checks} unit="건" />
                  <Stat
                    label="사실이 덜어낸 오탐"
                    value={usage.cleared_by_facts}
                    unit="건"
                    tone="ok"
                  />
                </dl>
                <p className="mt-5 border-t border-line pt-4 text-[14px] leading-relaxed text-sub">
                  검사 <strong className="font-bold text-ink">{usage.checks}건</strong>을 처리하는 동안
                  부른 AI 호출은{" "}
                  <strong className="font-bold text-ok">
                    {usage.llm_calls_serving_checks}번
                  </strong>
                  입니다. 부품 <strong className="font-bold text-ink">{usage.parts}개</strong>는 검사와
                  무관하게 미리 한 번씩 읽어 뒀고, 모든 검사가 그 사실을 그대로 씁니다.{" "}
                  <span className="text-mute">
                    검사가 늘어도 이 숫자는 0입니다. 비용은 검사 횟수가 아니라 처음 보는 부품에서만 늡니다.
                  </span>
                </p>
                <p className="mt-3 text-[13px] leading-relaxed text-mute">
                  검사 수는 배포할 때마다 0부터 다시 셉니다. 영구 저장 장치를 쓰지 않기 때문입니다.
                  부품과 사실 수는 저장소에 커밋된 파일에서 서버가 뜰 때 다시 심으므로 배포와
                  무관합니다.
                </p>
              </>
            ) : (
              <p className="text-[14px] leading-relaxed text-sub">
                지금은 서버에서 숫자를 가져오지 못했습니다. 서버가 잠들어 있거나 배포 중일 수
                있습니다. <span className="text-mute">추정치를 대신 보여드리지 않습니다.</span>
              </p>
            )}
          </div>
        </section>

        {/* ── 요금제 ───────────────────────────────────────────── */}
        <h2 className="mb-2 text-[19px] font-extrabold tracking-tight md:text-[22px]">
          그래서 이렇게 받으려 합니다
        </h2>
        <p className="mb-7 max-w-2xl text-[15px] leading-relaxed text-sub">
          돈이 드는 자리에서만 받습니다. 검사 횟수로는 받지 않습니다.
        </p>

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
            price="준비 중"
            note="개인 · 소규모"
            lines={[
              "무료의 모든 것",
              "아직 안 읽은 부품 데이터시트 읽기 요청",
              "규칙 발견 루프 — 내 보드에서 새 규칙 찾기",
              "결과 보관과 비공개 링크",
            ]}
          />
          <Plan
            name="팀"
            price="준비 중"
            note="발주가 잦은 팀"
            lines={[
              "Pro의 모든 것",
              "CI 연동 — 회로도가 바뀐 PR에서 자동 검사",
              "사내 부품 사실 등록 (공개 DB와 분리)",
              "사내 규칙 추가",
            ]}
          />
        </div>

        <div className="rounded-card border border-warn/25 bg-warn-weak p-6">
          <p className="mb-2 text-[15px] font-extrabold text-ink">
            아직 결제 기능이 없습니다.
          </p>
          <p className="text-[14px] leading-relaxed text-sub">
            "준비 중"이라고 적은 것은 아직 만들지 않았다는 뜻입니다. 되는 것처럼 보이는 결제 화면을
            먼저 만들지 않았습니다. 지금 쓰실 수 있는 것은 무료 항목 전부이고, 그건 로그인 없이 바로
            됩니다.
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

function Cost({ head, body, tone }: { head: string; body: string; tone?: "key" }) {
  return (
    <div className={`border-l-2 py-1 pl-4 ${tone === "key" ? "border-brand" : "border-line"} mb-5`}>
      <p className="mb-1 text-[15px] font-extrabold tracking-tight md:text-[16px]">{head}</p>
      <p className="text-[14px] leading-relaxed text-sub md:text-[15px]">{body}</p>
    </div>
  );
}

function Stat({
  label,
  value,
  unit,
  tone,
}: {
  label: string;
  value: number;
  unit: string;
  tone?: "ok";
}) {
  return (
    <div>
      <dt className="mb-1 text-[12px] font-bold text-mute">{label}</dt>
      <dd
        className={`text-[24px] font-extrabold tracking-tight md:text-[27px] ${
          tone === "ok" ? "text-ok" : "text-ink"
        }`}
      >
        {value.toLocaleString("ko-KR")}
        <span className="ml-0.5 text-[13px] font-bold text-mute">{unit}</span>
      </dd>
    </div>
  );
}

function Plan({
  name,
  price,
  note,
  lines,
  limit,
  highlight,
}: {
  name: string;
  price: string;
  note: string;
  lines: string[];
  limit?: string;
  highlight?: boolean;
}) {
  return (
    <section
      className={`flex flex-col rounded-card border p-6 ${
        highlight ? "border-brand/30 bg-surface shadow-card" : "border-line bg-surface"
      }`}
    >
      <p className="mb-1 text-[13px] font-bold text-sub">{name}</p>
      <p
        className={`text-[26px] font-extrabold tracking-tight ${
          highlight ? "text-ink" : "text-mute"
        }`}
      >
        {price}
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
    </section>
  );
}
