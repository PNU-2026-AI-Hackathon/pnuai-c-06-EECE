import { Link } from "react-router-dom";

import { Header } from "../components/Layout";

/**
 * 검증 결과 — **우리가 틀리는 지점을 먼저 적는 화면.**
 *
 * ## 왜 이 화면을 만들었나
 *
 * 이 내용은 원래 README 3.6절에만 있었다. **우리가 가진 것 중 가장 센 자산인데
 * 서비스 안에서는 볼 방법이 없었다** — 문서를 읽는 사람만 닿았다.
 *
 * 검사 도구를 파는데 「얼마나 틀리는지」를 안 보여주면, 사는 쪽은 우리 말을
 * 믿는 수밖에 없다. 그건 우리가 하려는 일의 반대다.
 *
 * ## 이 화면이 지켜야 하는 것
 *
 * **좋은 숫자만 싣지 않는다.** 홀드아웃에서 14건이 터진 것, 그게 「같은 데이터로
 * 재고 있었다」는 뜻이었다는 것까지 그대로 적는다. 그 문단이 빠지면 이 화면은
 * 광고가 되고, 광고는 이 제품이 파는 것과 정반대다 (헌법 2-2 · 2-4).
 */
export function EvidencePage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-3xl px-5 py-14 md:py-20">
        <p className="mb-3 text-[13px] font-bold uppercase tracking-[0.14em] text-mute">
          검증 결과
        </p>
        <h1 className="mb-5 text-[30px] font-extrabold leading-[1.25] tracking-tight md:text-[42px]">
          저희가 어디서 틀리는지
          <br />
          먼저 적습니다.
        </h1>
        <p className="mb-4 max-w-2xl text-[16.5px] leading-relaxed text-sub">
          검사 도구가 「몇 개를 찾았다」고만 말하면 그건 확인할 수 없는 주장입니다.
          중요한 건 <strong className="font-bold text-ink">멀쩡한 것을 몇 번 잘못 짚느냐</strong>고,
          그건 재기 전에는 아무도 모릅니다.
        </p>
        <p className="mb-12 max-w-2xl text-[15px] leading-relaxed text-mute">
          아래 숫자는 전부 저장소에서 다시 돌려 확인할 수 있습니다.
          잘 나온 것만 고르지 않았습니다.
        </p>

        {/* ── 요약 띠 ─────────────────────────────────────────── */}
        <dl className="mb-14 grid grid-cols-2 gap-px overflow-hidden rounded-card border border-line bg-line sm:grid-cols-4">
          {[
            { k: "검출", v: "17/17", u: "", tone: "ink" },
            { k: "주입 오탐", v: "0", u: "%", tone: "ok" },
            { k: "홀드아웃", v: "38", u: "보드", tone: "ink" },
            { k: "테스트", v: "892", u: "개", tone: "ink" },
          ].map((m) => (
            <div key={m.k} className="bg-surface px-4 py-4">
              <dt className="text-[12px] font-semibold text-mute">{m.k}</dt>
              <dd
                className={`mt-1 text-[24px] font-extrabold tabular-nums ${
                  m.tone === "ok" ? "text-ok" : "text-ink"
                }`}
              >
                {m.v}
                <span className="ml-0.5 text-[13px] font-bold text-mute">{m.u}</span>
              </dd>
            </div>
          ))}
        </dl>

        {/* ── 1. 주입 결함 ────────────────────────────────────── */}
        <Block
          n="01"
          title="라벨이 있는 케이스에 돌립니다"
          lede="결함을 일부러 심은 보드와, 겉모습이 비슷한데 멀쩡한 보드를 짝으로 둡니다. 뒤쪽이 오탐율의 전부입니다."
        >
          <Figures
            rows={[
              ["검출", "17 / 17", "100%", "ok"],
              ["오탐", "0 / 14", "0%", "ok"],
            ]}
          />
          <Limit>
            이 숫자가 재는 것은 <strong className="font-bold text-ink">케이스 27개</strong>(합성 25 · 실측 2)입니다.
            <br />
            <strong className="font-bold text-ink">못 재는 것 — 남의 보드에서의 재현율.</strong>{" "}
            공개 저장소에는 작동하는 보드만 올라와서 라벨된 결함이 안 남습니다.
          </Limit>
          <p className="mt-4 text-[14px] leading-relaxed text-mute">
            위 한계 문단은 <strong className="font-semibold text-sub">측정 도구가 스스로 출력합니다.</strong>{" "}
            숫자만 떼어 인용되는 것을 막으려고 코드에 넣었습니다.
          </p>
        </Block>

        {/* ── 2. 홀드아웃 ─────────────────────────────────────── */}
        <Block
          n="02"
          title="한 번도 안 써본 보드 38개에 처음 댔습니다"
          lede="여기서 저희가 스스로를 속이고 있었다는 게 드러났습니다."
        >
          <div className="overflow-x-auto rounded-card border border-line bg-surface">
            <table className="w-full text-[14.5px]">
              <thead>
                <tr className="border-b border-line text-[12px] font-bold text-mute">
                  <th className="px-4 py-3 text-left">시점</th>
                  <th className="px-4 py-3 text-right">발견</th>
                  <th className="px-4 py-3 text-left">성격</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-line">
                  <td className="px-4 py-3 text-sub">처음</td>
                  <td className="px-4 py-3 text-right font-bold tabular-nums text-crit">14건</td>
                  <td className="px-4 py-3 text-sub">오탐 9 · 미결 4 · 진짜 1</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-sub">오탐 뿌리 3개 수정 후</td>
                  <td className="px-4 py-3 text-right font-extrabold tabular-nums text-ok">1건</td>
                  <td className="px-4 py-3 text-sub">진짜 하나만</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-5 text-[15.5px] leading-relaxed text-sub">
            같은 보드 6개로 오탐 0건을 만들어 놓고 있었는데,{" "}
            <strong className="font-bold text-ink">새 보드에 처음 대니 14건이 나왔습니다.</strong>{" "}
            같은 데이터로 재고 있었다는 뜻입니다. 이 문단을 지우면 위의 0% 가 거짓이 됩니다.
          </p>
        </Block>

        {/* ── 3. LLM 대조 ─────────────────────────────────────── */}
        <Block
          n="03"
          title="같은 보드 28개를 LLM 과 나란히 돌렸습니다"
          lede="정확도가 아니라 「끝까지 근거를 대는가」를 봤습니다."
        >
          <div className="overflow-x-auto rounded-card border border-line bg-surface">
            <table className="w-full text-[14.5px]">
              <thead>
                <tr className="border-b border-line text-[12px] font-bold text-mute">
                  <th className="px-4 py-3 text-left"> </th>
                  <th className="px-4 py-3 text-right">Prefab</th>
                  <th className="px-4 py-3 text-right">Claude Sonnet 5</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-line">
                  <td className="px-4 py-3 text-sub">끝까지 읽은 보드</td>
                  <td className="px-4 py-3 text-right font-extrabold tabular-nums text-ok">28 / 28</td>
                  <td className="px-4 py-3 text-right tabular-nums text-sub">22 / 28</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-sub">경고 중 근거를 끝까지 댄 비율</td>
                  <td className="px-4 py-3 text-right font-extrabold tabular-nums text-ok">100% (16/16)</td>
                  <td className="px-4 py-3 text-right tabular-nums text-sub">77% (34/44)</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-5 text-[15.5px] leading-relaxed text-sub">
            LLM 은 입력이 큰 보드 6개를 통째로 건너뛰었고, 낸 경고 44건 중 10건은{" "}
            <em className="not-italic rounded bg-warn-weak px-1 text-ink">
              "파일을 보지 못해 확인할 수 없음"
            </em>{" "}
            이라고 적으면서도 경고로 냈습니다.
          </p>
          <Limit>
            측정 조건은 <strong className="font-bold text-ink">양쪽이 다 읽은 22개 보드 기준</strong>입니다.
            <br />
            이건 「LLM 보다 똑똑하다」는 뜻이 아닙니다. <strong className="font-bold text-ink">같은
            입력에 같은 답을 내느냐</strong>의 차이입니다.
          </Limit>

          <div className="mt-6 rounded-card border border-ok/30 bg-ok-weak p-5">
            <p className="mb-2 text-[15px] font-extrabold text-ink">
              그리고 그 실험에서 규칙이 하나 나왔습니다
            </p>
            <p className="text-[14.5px] leading-relaxed text-sub">
              Sonnet 이 <em className="not-italic font-semibold text-ink">"U3 15번 핀이 두 넷에 있다"</em>{" "}
              고 지적했고, 넷리스트를 열어 보니 사실이었습니다 — EEPROM 데이터 선 두 개가 한 핀에
              물려 있었습니다. <strong className="font-bold text-ink">저희 규칙 14개 중 어느 것도 그
              모양을 안 보고 있었습니다.</strong> 그게 지금 규칙 <strong className="font-bold text-ink">R17</strong> 입니다.
            </p>
          </div>
        </Block>

        {/* ── 4. 실전 ─────────────────────────────────────────── */}
        <Block
          n="04"
          title="남의 실제 보드에서 찾아 제보했습니다"
          lede="합성 케이스가 아니라, 오늘도 공개돼 있는 프로젝트입니다."
        >
          <p className="mb-4 text-[15.5px] leading-relaxed text-sub">
            오픈소스 ESP32 보드를 훑다가 어긋난 핀 상수를 찾았습니다. 백라이트가 납땜에 맞춰
            GPIO 19 로 옮겨졌는데 다른 파일의 상수는 25 에 그대로 남아 있었고,{" "}
            <strong className="font-bold text-ink">25 는 그 보드에서 디스플레이 데이터선입니다.</strong>
          </p>
          <a
            href="https://github.com/FForzano/xgsail-e1/issues/5"
            target="_blank"
            rel="noreferrer"
            className="btn-primary"
          >
            제보한 이슈 보기 →
          </a>
        </Block>

        {/* ── 닫기 ────────────────────────────────────────────── */}
        <div className="mt-16 border-t border-line pt-10">
          <p className="mb-6 max-w-2xl text-[16px] leading-relaxed text-sub">
            <strong className="font-bold text-ink">오탐이 저희의 최우선 적입니다.</strong>{" "}
            검사 도구는 오탐률이 높으면 사흘 만에 꺼집니다. 규칙을 늘리는 것보다
            잘못 짚는 것을 줄이는 쪽이 항상 먼저입니다.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/r/chk_sample01" className="btn-primary">
              실제 검사 결과 보기
            </Link>
            <Link
              to="/check"
              className="inline-flex min-h-[44px] items-center rounded-block px-3 text-[15px] font-bold text-sub hover:text-ink"
            >
              내 보드로 해보기
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}

function Block({
  n,
  title,
  lede,
  children,
}: {
  n: string;
  title: string;
  lede: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-14">
      <div className="mb-2 flex items-baseline gap-3">
        <span className="data text-[13px] font-bold text-mute">{n}</span>
        <h2 className="text-[21px] font-extrabold leading-snug tracking-tight md:text-[25px]">
          {title}
        </h2>
      </div>
      <p className="mb-5 max-w-2xl text-[15.5px] leading-relaxed text-sub">{lede}</p>
      {children}
    </section>
  );
}

function Figures({ rows }: { rows: [string, string, string, string][] }) {
  return (
    <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-card border border-line bg-line">
      {rows.map(([k, v, pct, tone]) => (
        <div key={k} className="bg-surface px-5 py-4">
          <dt className="text-[13px] font-semibold text-mute">{k}</dt>
          <dd className="mt-1 flex items-baseline gap-2">
            <span className="text-[24px] font-extrabold tabular-nums text-ink">{v}</span>
            <span
              className={`text-[14px] font-bold tabular-nums ${
                tone === "ok" ? "text-ok" : "text-sub"
              }`}
            >
              {pct}
            </span>
          </dd>
        </div>
      ))}
    </dl>
  );
}

/** 이 숫자가 **못 재는 것**. 좋은 숫자 옆에 항상 붙인다. */
function Limit({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-4 rounded-block border border-warn/25 bg-warn-weak px-4 py-3.5 text-[14px] leading-relaxed text-sub">
      {children}
    </p>
  );
}
