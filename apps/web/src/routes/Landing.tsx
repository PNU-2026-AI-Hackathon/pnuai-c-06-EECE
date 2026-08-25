import { Link } from "react-router-dom";

import { AuthCta } from "../components/AuthCta";

import { Header } from "../components/Layout";
import { ReportPreview } from "../components/ReportPreview";

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
 *   6. LLM이면 되지 않나   재봤다 — 숫자로 답한다
 *   7. 지금 뭘 하나       CTA
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
        <VsLlm />
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
        <AuthCta />
        {/*
          **누구를 위한 것인지 한 번도 말하지 않고 있었다.** 그리고 「넷리스트」가
          설명 없이 등장한다 — KiCad 사용자는 알지만 다른 도구를 쓰는 사람은
          자기 파일 중 무엇을 올려야 하는지 모른다. 여기서 둘 다 해결한다.
        */}
        <p className="mt-4 text-[13px] leading-relaxed text-mute">
          ESP32 · Raspberry Pi Pico 계열 보드를 만드는 분들을 위한 도구입니다.
          <br />
          설치는 없습니다 — 회로도 도구에서 내보낸{" "}
          <strong className="font-semibold text-sub">넷리스트 파일</strong> 하나면 시작합니다
          (KiCad · Altium · EasyEDA · Flux).
        </p>

        {/* **무엇을 받는지 먼저 보여준다.** 로그인 벽이 생긴 만큼 더 필요해졌다 */}
        <div className="mt-10 max-w-2xl">
          <ReportPreview />
          <p className="mt-3 text-[13px] text-mute">
            실제 보드를 검사한 결과입니다. 판정마다 회로도 · 코드 · 부품 근거가 붙습니다.
          </p>
        </div>
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
          {/* 진실은 API 의 `catalog.py` 다. 여기 숫자는 사본이라 규칙이 늘면 같이 고친다.
              검사 화면은 응답의 rules_total 을 쓰므로 이 값에 안 기댄다. */}
          <strong className="font-bold text-ink">15가지</strong>를 봅니다.
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

/**
 * 「그냥 LLM 한테 물어보면 되는 거 아닌가」 에 대한 답.
 *
 * **이 화면에서 유일하게 남의 도구와 직접 비교하는 자리다.** 그래서 규칙을 두 개 건다 —
 *
 *   1. 우리가 실제로 측정한 것만 적는다. 측정 조건을 각주로 같이 낸다
 *   2. **낮을수록 좋은 것과 높을수록 좋은 것을 섞지 않는다.** 막대 두 개 다
 *      「길수록 우리가 낫다」로 방향을 맞춘다. 안 그러면 훑어보는 사람이 거꾸로 읽는다
 *
 * 색: 우리는 brand-strong(#1B64DA), 상대는 sub(#4E5968). 상대를 빨강으로 칠하지 않는다 —
 * 판정 색(crit·warn·ok)은 검사 결과 전용이고, 광고에 쓰면 그 뜻이 닳는다.
 * 두 색은 색맹 분리 ΔE 18.1 · 표면 대비 3:1 을 넘고, 신원은 색이 아니라 **막대마다 붙은
 * 이름표**가 진다.
 */
function VsLlm() {
  return (
    <Section>
      <div className="max-w-3xl">
        <Eyebrow>그냥 LLM에 물어보면 안 되나요</Eyebrow>
        <h2 className="mb-5 text-[24px] font-extrabold leading-snug md:text-[32px]">
          같은 보드 28개를 Claude Sonnet 5와 나란히 돌렸습니다.
        </h2>
        <p className="mb-9 text-[16px] leading-relaxed text-sub">
          한 번도 검사에 써본 적 없는 공개 회로도 28개에 양쪽 다 같은 파일을 넣었습니다.
          <strong className="font-bold text-ink">
            {" "}큰 보드는 LLM 이 여섯 개를 통째로 건너뛰었고, 낸 경고 넷 중 하나는
            근거를 못 댔습니다.
          </strong>
        </p>

        <div className="grid gap-8 sm:grid-cols-2">
          <BarPair
            title="끝까지 읽은 보드"
            note="큰 보드는 LLM이 통째로 건너뜁니다. 안 본 보드는 “문제 없음”이 아니라 모르는 보드입니다."
            unit="개"
            max={28}
            bars={[
              { name: "Prefab", value: 28, ours: true },
              { name: "Sonnet 5", value: 22 },
            ]}
          />
          <BarPair
            title="경고 중 근거를 끝까지 댄 비율"
            note="“확인할 수 없다”고 적어 놓고 그대로 경고로 낸 것을 뺀 값입니다. 우리는 그런 자리를 경고가 아니라 미결로 냅니다."
            unit="%"
            max={100}
            bars={[
              { name: "Prefab", value: 100, ours: true, detail: "16건 중 16건" },
              { name: "Sonnet 5", value: 77, detail: "44건 중 34건" },
            ]}
          />
        </div>

        <figure className="mt-9 overflow-hidden rounded-card border border-line bg-surface">
          <figcaption className="flex flex-wrap items-center gap-2 border-b border-line px-5 py-2.5">
            <span className="rounded-chip bg-surface-2 px-2 py-0.5 text-[11px] font-bold text-sub">
              경고
            </span>
            <span className="text-[13px] font-semibold text-sub">
              Sonnet 5가 낸 것 그대로
            </span>
          </figcaption>
          <div className="px-5 py-4">
            <p className="text-[15px] leading-relaxed text-sub">
              “IO10은 부팅 시 상태가 불확실한 핀인데 부저 드라이브에 직결되어 있어
              버저가 순간 구동될 수 있음.{" "}
              <mark className="bg-warn-weak font-bold text-warn">
                다만 door_entry.h를 보지 못해
              </mark>{" "}
              IO10이 실제로 어떤 GPIO 번호에 매핑되는지는 확인할 수 없음.”
            </p>
            <p className="mt-4 text-[14px] leading-relaxed text-mute">
              읽지 못한 파일을 근거로 경고를 냈습니다. 44건 중 10건이 이런
              모양이었습니다. 우리는 같은 상황을 경고가 아니라{" "}
              <strong className="font-bold text-ink">미결</strong>로 내고,
              무엇이 있으면 풀리는지를 적습니다.
            </p>
          </div>
        </figure>

        <div className="mt-6 rounded-card border border-line bg-brand-weak px-5 py-4">
          <p className="text-[15px] leading-relaxed text-ink">
            <strong className="font-bold">
              같은 파일을 두 번 넣으면 같은 결과가 나옵니다.
            </strong>{" "}
            판정하는 코드는 모델을 부르지 않습니다. 회로도가 우리 서버 밖으로
            나가지 않는 이유도 그것입니다.
          </p>
        </div>

        <p className="mt-5 text-[13px] leading-relaxed text-mute">
          측정 조건 — 공개 저장소 28곳, 2026년 8월. 회로도와 펌웨어를 양쪽에 똑같이
          넣었고, 막대는 양쪽이 다 읽은 22개 보드 기준입니다. 셀 수 있는 것만 적었습니다.{" "}
          <a
            href="https://github.com/PNU-2026-AI-Hackathon/pnuai-c-06-EECE/blob/main/apps/api/scripts/llm_baseline.py"
            className="font-semibold text-brand-strong hover:underline"
          >
            측정 스크립트
          </a>
          는 공개돼 있습니다.
        </p>
      </div>
    </Section>
  );
}

/** 막대 두 개짜리 비교 하나. 값은 막대마다 직접 붙는다 — 축도 범례도 두지 않는다.
 *
 * **막대 둘 다 「길수록 우리가 낫다」여야 한다.** 처음에 두 번째 그림을 건수로 그렸다가
 * Sonnet 막대가 더 길어져서 정반대로 읽혔다. 비율로 바꿔 방향을 맞췄다. */
function BarPair({
  title,
  note,
  unit,
  max,
  bars,
}: {
  title: string;
  note: string;
  unit: string;
  max: number;
  bars: { name: string; value: number; ours?: boolean; detail?: string }[];
}) {
  return (
    <figure>
      <figcaption className="mb-4 text-[15px] font-bold text-ink">
        {title}
      </figcaption>
      <div className="space-y-3.5">
        {bars.map((b) => (
          <div key={b.name}>
            <div className="mb-1.5 flex items-baseline justify-between gap-2">
              <span
                className={
                  b.ours
                    ? "text-[13px] font-bold text-ink"
                    : "text-[13px] font-semibold text-mute"
                }
              >
                {b.name}
              </span>
              <span
                className={
                  b.ours
                    ? "text-[15px] font-extrabold text-ink"
                    : "text-[15px] font-bold text-sub"
                }
              >
                {b.value}
                <span className="text-[12px] font-semibold text-mute">
                  {unit}
                  {b.detail ? ` · ${b.detail}` : ""}
                </span>
              </span>
            </div>
            {/* 막대는 요소 하나다. 값은 위에 이미 있으므로 안에 글자를 넣지 않는다 */}
            <div
              className="h-2.5 overflow-hidden rounded-chip bg-surface-2"
              role="img"
              aria-label={`${b.name} ${b.value}${unit}`}
            >
              <div
                className="h-full rounded-chip"
                style={{
                  width: `${Math.max(2, (b.value / max) * 100)}%`,
                  backgroundColor: b.ours ? "#1B64DA" : "#4E5968",
                }}
              />
            </div>
          </div>
        ))}
      </div>
      <p className="mt-3 text-[13px] leading-relaxed text-mute">{note}</p>
    </figure>
  );
}

function Closing() {
  return (
    <Section tone="raised">
      <div className="max-w-3xl">
        <h2 className="mb-4 text-[26px] font-extrabold leading-snug md:text-[34px]">
          지금 검사해 보세요.
        </h2>
        <p className="mb-7 text-[16px] leading-relaxed text-sub">
          넷리스트 파일 하나면 시작합니다. 이메일만 있으면 계정이 만들어집니다.{" "}
          <Link
            to="/pricing"
            className="font-bold text-brand-strong hover:underline"
          >
            검사는 무료입니다
          </Link>{" "}
          — 원가가 그렇게 생겼기 때문이고, 그 원가를 그대로 적어 뒀습니다.
        </p>
        <AuthCta />
      </div>
    </Section>
  );
}

/**
 * 푸터 — **정식 서비스의 얼굴이다.**
 *
 * 대회·학교·팀원 이름을 여기 두지 않는다. 처음 온 사람에게 그 정보는
 * "이건 과제물이구나" 라는 신호이고, 돈을 낼 이유를 스스로 지운다.
 *
 * ## 유료로 전환하기 전에 반드시 채워야 하는 것
 *
 * 전자상거래법상 **유료 판매를 시작하는 순간** 아래가 푸터에 있어야 한다.
 * 지금은 사업자 등록 전이라 **비워 두었다. 지어내지 않는다** (헌법 2-2).
 *
 *   상호 · 대표자명 · 사업자등록번호 · 통신판매업 신고번호
 *   사업장 주소 · 고객문의 전화 · 이메일
 *   이용약관 · 개인정보처리방침(별도 문서) · 환불 정책
 *
 * 등록이 끝나면 `BUSINESS` 를 채우고 아래 주석을 지운다.
 * **채우기 전에는 결제 화면을 열지 않는다.**
 */
//: 지금 실제로 사람이 읽는 문의 창구. 유료 전환 시 지원 메일로 교체한다.
const SUPPORT_URL =
  "https://github.com/PNU-2026-AI-Hackathon/pnuai-c-06-EECE/issues/new";

function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-line">
      <div className="mx-auto max-w-5xl px-5 py-10 text-[13px] text-mute">
        <div className="mb-5 flex flex-wrap items-center gap-x-5">
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
          <Link
            to="/check"
            className="inline-flex min-h-[44px] items-center font-semibold hover:text-ink"
          >
            검사하기
          </Link>
          {/* **실제로 닿는 창구만 건다.** 안 가는 메일 주소를 그럴듯하게 적는 것이
              제일 나쁘다 — 유료 사용자가 환불을 요청할 때 그 주소로 보낸다.
              도메인과 지원 메일이 준비되면 여기를 mailto 로 바꾼다. */}
          <a
            href={SUPPORT_URL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-[44px] items-center font-semibold hover:text-ink"
          >
            문의하기
          </a>
        </div>
        <p className="leading-relaxed">
          © {year} Prefab · 발주 전에 회로도와 펌웨어를 대조합니다
        </p>
      </div>
    </footer>
  );
}
