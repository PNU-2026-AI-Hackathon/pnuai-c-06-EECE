import { Link } from "react-router-dom";

import { Header } from "../components/Layout";

/**
 * 홍보 화면 — **검사 앱보다 앞에 선다.**
 *
 * 한동안 `/` 가 곧 업로드 폼이었다. 넷리스트 파일을 들고 오는 사람에게는 그게 맞지만,
 * **처음 온 사람은 이 도구가 무엇인지부터 모른다.** 파일도 없다.
 *
 * ## 참고한 것과 안 따라한 것
 *
 * Traceformer(직접 경쟁)·Linear·Semgrep 세 곳의 랜딩을 실제로 열어 구조만 봤다.
 * 공통점이 하나 있었다 — **셋 다 자기 도구가 낸 결과를 화면에 안 보여준다.**
 * 로고와 수치로 신뢰를 만든다.
 *
 * 우리는 그 방법을 쓸 수 없다. 고객 로고도 사용자 수도 없다.
 * 대신 그들이 못 하는 것을 할 수 있다 — **실제 결과를 로그인 없이 그 자리에서 보여주는 것.**
 * 그래서 이 화면의 중심은 발견 카드이고, 제일 큰 버튼이 「예시 결과 보기」다.
 *
 * ## 섹션 순서
 *
 * 사용자가 묻는 순서다. 기능 목록이 아니다.
 *
 *   1. 이게 뭔가          동사 + 결과
 *   2. 왜 필요한가        컴파일도 되고 업로드도 되는 버그
 *   3. 진짜인가           우리 보드에서 실제로 있었던 일
 *   4. 어떻게 아나        세 자료를 대조한다
 *   5. 지어내진 않나      근거가 붙는다 · 모르면 모른다고 한다
 *   6. 지금 뭘 하나       CTA
 */
export function LandingPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main>
        <Hero />
        <Problem />
        <RealCase />
        <How />
        <Evidence />
        <Closing />
      </main>
      <Footer />
    </div>
  );
}

/** 섹션 하나. 배경색을 번갈아 쓰지 않는다 — 흰 면은 강조할 때만 쓴다 */
function Section({
  children,
  tone = "plain",
}: {
  children: React.ReactNode;
  tone?: "plain" | "raised";
}) {
  return (
    <section
      className={tone === "raised" ? "border-y border-line bg-surface" : ""}
    >
      <div className="mx-auto max-w-5xl px-5 py-16 md:py-24">{children}</div>
    </section>
  );
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-3 text-[13px] font-bold text-brand-strong">{children}</p>
  );
}

function Hero() {
  return (
    <Section>
      <div className="max-w-3xl">
        <h1 className="mb-5 text-[32px] font-extrabold leading-[1.25] md:text-[52px] md:leading-[1.15]">
          보드를 발주하기 전에,
          <br />
          <span className="text-brand-strong">코드와 회로도가 어긋난 곳</span>을
          찾습니다.
        </h1>
        <p className="mb-8 text-[17px] leading-relaxed text-sub md:text-[19px]">
          컴파일도 되고 업로드도 되는데 보드가 안 도는 버그가 있습니다. 문제가
          코드와 회로도 <strong className="font-bold text-ink">사이</strong>에
          있어서 어느 쪽 검사에도 안 걸리기 때문입니다.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Link to="/r/chk_sample01" className="btn-primary">
            예시 검사 결과 보기
          </Link>
          <Link
            to="/check"
            className="inline-flex min-h-[44px] items-center rounded-block px-3 text-[15px] font-bold text-sub hover:text-ink"
          >
            내 파일로 검사하기
          </Link>
        </div>
        <p className="mt-4 text-[13px] text-mute">
          가입도 설치도 없습니다. 넷리스트 파일 하나면 시작합니다.
        </p>
      </div>
    </Section>
  );
}

function Problem() {
  return (
    <Section tone="raised">
      <div className="max-w-3xl">
        <Eyebrow>왜 필요한가</Eyebrow>
        <h2 className="mb-5 text-[24px] font-extrabold leading-snug md:text-[32px]">
          제일 비싼 버그는 컴파일도 되고 업로드도 됩니다.
        </h2>
        <p className="mb-6 text-[16px] leading-relaxed text-sub">
          코드는 회로도를 모르고, 회로도 검사는 코드를 모릅니다. 그래서 둘
          사이에 생긴 어긋남은 누구도 안 봅니다. 보드가 도착해서 안 켜질 때 알게
          됩니다.
        </p>
        <div className="rounded-card border border-line bg-bg px-5 py-4">
          <pre className="data overflow-x-auto whitespace-pre text-sub">{`// config.h
#define LED_PIN 34

// main.cpp
pinMode(LED_PIN, OUTPUT);   // 컴파일 통과. 업로드 성공. LED는 안 켜짐.`}</pre>
        </div>
        <p className="mt-4 text-[14px] leading-relaxed text-mute">
          구형 ESP32의 GPIO34는 입력 전용입니다. 컴파일러도, 회로도 DRC도 이걸
          모릅니다.
        </p>
      </div>
    </Section>
  );
}

function RealCase() {
  return (
    <Section>
      <div className="max-w-3xl">
        <Eyebrow>실제로 있었던 일</Eyebrow>
        <h2 className="mb-6 text-[24px] font-extrabold leading-snug md:text-[32px]">
          우리 보드가 이걸로 고장 났고, 이 도구가 그 자리를 짚었습니다.
        </h2>
        <ol className="space-y-4">
          {[
            {
              when: "8월 21일",
              text: "하드웨어 담당의 보고 — “LED가 ON은 되는데 OFF가 안 되는 게 문제야.”",
            },
            {
              when: "같은 날",
              text: "검사가 그 네트를 짚었습니다. 3.3V로는 5V 릴레이 입력을 끌 수 없다는 것.",
            },
            {
              when: "그날 저녁",
              text: "트랜지스터를 넣어 고쳤고, 사람이 오가는 대로 켜지고 꺼지는 것을 확인했습니다.",
            },
            {
              when: "고친 뒤",
              text: "같은 검사를 다시 돌리니 그 경고가 사라졌습니다.",
            },
          ].map((s) => (
            <li key={s.when} className="flex gap-4">
              <span className="w-[72px] shrink-0 pt-0.5 text-[13px] font-bold text-mute">
                {s.when}
              </span>
              <span className="text-[16px] leading-relaxed text-sub">
                {s.text}
              </span>
            </li>
          ))}
        </ol>
        <p className="mt-6 rounded-block bg-crit-weak px-4 py-3.5 text-[14px] leading-relaxed text-crit">
          <strong className="font-bold">PCB는 이미 발주한 뒤였습니다.</strong>{" "}
          그래서 그 보드는 손으로 고쳐야 했습니다. 발주 전에 잡는 것이 이 도구가
          하려는 일입니다.
        </p>
      </div>
    </Section>
  );
}

function How() {
  const rows = [
    { k: "회로도", v: "어느 핀이 어디에 이어졌는지" },
    { k: "펌웨어", v: "코드가 그 핀을 어떻게 쓰는지" },
    { k: "데이터시트", v: "그 부품이 실제로 견디는 값" },
  ];
  return (
    <Section tone="raised">
      <div className="max-w-3xl">
        <Eyebrow>어떻게 아나</Eyebrow>
        <h2 className="mb-6 text-[24px] font-extrabold leading-snug md:text-[32px]">
          세 가지를 나란히 놓고 대조합니다.
        </h2>
        <dl className="mb-6 divide-y divide-line border-y border-line">
          {rows.map((r) => (
            <div key={r.k} className="flex flex-wrap gap-x-6 gap-y-1 py-4">
              <dt className="w-[88px] shrink-0 text-[15px] font-bold">{r.k}</dt>
              <dd className="text-[15px] leading-relaxed text-sub">{r.v}</dd>
            </div>
          ))}
        </dl>
        <p className="text-[16px] leading-relaxed text-sub">
          셋이 서로 다른 말을 하는 자리가 어긋난 곳입니다. 지금{" "}
          <strong className="font-bold text-ink">14가지</strong>를 봅니다.
        </p>
      </div>
    </Section>
  );
}

function Evidence() {
  return (
    <Section>
      <div className="max-w-3xl">
        <Eyebrow>지어내지 않습니다</Eyebrow>
        <h2 className="mb-6 text-[24px] font-extrabold leading-snug md:text-[32px]">
          모든 판정에 열어볼 수 있는 근거가 붙습니다.
        </h2>

        <figure className="mb-6 overflow-hidden rounded-card border border-line bg-surface">
          <figcaption className="flex items-center gap-2 border-b border-line px-5 py-2.5">
            <span className="rounded-chip bg-crit-weak px-2 py-0.5 text-[11px] font-bold text-crit">
              치명
            </span>
            <span className="text-[13px] font-semibold text-sub">
              실제 검사 결과에서
            </span>
          </figcaption>
          <div className="px-5 py-4">
            <p className="mb-3 text-[15px] leading-relaxed">
              코드가 <span className="data">D10</span> 핀을 출력으로 구동합니다.
              그런데 회로도에서 이 핀은 아무 데도 이어져 있지 않습니다.
            </p>
            <dl className="grid gap-2 text-[13px] sm:grid-cols-2">
              <div className="rounded-block bg-surface-2 px-3 py-2.5">
                <dt className="label mb-1">회로도</dt>
                <dd className="data text-sub">U1.D10 → N/C</dd>
              </div>
              <div className="rounded-block bg-surface-2 px-3 py-2.5">
                <dt className="label mb-1">코드</dt>
                <dd className="data text-sub">
                  main.ino:16
                  <br />
                  const int LED_PIN = D10;
                </dd>
              </div>
            </dl>
          </div>
        </figure>

        <p className="text-[16px] leading-relaxed text-sub">
          데이터시트에서 읽은 값에는{" "}
          <strong className="font-bold text-ink">쪽 번호와 원문</strong>이
          붙습니다. 확인하지 못한 것은{" "}
          <strong className="font-bold text-ink">모른다고 적습니다</strong> —
          넘겨짚어 “이상 없음” 이라고 하지 않습니다.
        </p>
      </div>
    </Section>
  );
}

function Closing() {
  return (
    <Section tone="raised">
      <div className="max-w-3xl">
        <h2 className="mb-4 text-[26px] font-extrabold leading-snug md:text-[34px]">
          먼저 결과부터 보세요.
        </h2>
        <p className="mb-7 text-[16px] leading-relaxed text-sub">
          실제 보드를 검사한 결과가 그대로 열려 있습니다. 파일을 올리지 않아도
          됩니다.{" "}
          <Link
            to="/pricing"
            className="font-bold text-brand-strong hover:underline"
          >
            검사는 무료입니다
          </Link>{" "}
          — 원가가 그렇게 생겼기 때문이고, 그 원가를 그대로 적어 뒀습니다.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Link to="/r/chk_sample01" className="btn-primary">
            예시 검사 결과 보기
          </Link>
          <Link
            to="/check"
            className="inline-flex min-h-[44px] items-center rounded-block px-3 text-[15px] font-bold text-sub hover:text-ink"
          >
            내 파일로 검사하기
          </Link>
        </div>
      </div>
    </Section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto max-w-5xl px-5 py-10 text-[13px] text-mute">
        <div className="mb-4 flex flex-wrap items-center gap-x-5">
          <Link
            to="/pricing"
            className="inline-flex min-h-[44px] items-center font-semibold hover:text-ink"
          >
            요금
          </Link>
          <Link
            to="/privacy"
            className="inline-flex min-h-[44px] items-center font-semibold hover:text-ink"
          >
            데이터 처리 안내
          </Link>
          <a
            href="https://github.com/PNU-2026-AI-Hackathon/pnuai-c-06-EECE"
            className="inline-flex min-h-[44px] items-center font-semibold hover:text-ink"
          >
            소스 보기
          </a>
          <a
            href="https://github.com/PNU-2026-AI-Hackathon/pnuai-c-06-EECE/issues/new"
            className="inline-flex min-h-[44px] items-center font-semibold hover:text-ink"
          >
            문의하기
          </a>
        </div>
        <p className="leading-relaxed">
          Prefab · 부산대학교 2026 AI 해커톤 창업트랙 C-06 전전컴
          <br />
          박강현 · 조우진 · 유동훈 · 한지양 · 권지효
        </p>
      </div>
    </footer>
  );
}
