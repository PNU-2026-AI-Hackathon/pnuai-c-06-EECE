/**
 * 랜딩에 싣는 **리포트 미리보기.**
 *
 * 예전에는 「예시 검사 결과 보기」 버튼으로 진짜 리포트를 열어 줬다. 로그인 벽이
 * 생기면서 그 문은 닫혔고(8/24), 대신 **무엇을 받는지는 보여준다** — 방문자가
 * 회로도를 올리기 전까지 아무것도 못 보면 가입할 이유가 없다.
 *
 * ## 스크린샷을 쓰지 않는 이유
 *
 * 이미지는 화면 크기마다 흐려지고, 글자를 못 고르고, 화면 낭독기가 못 읽는다.
 * 같은 디자인 토큰으로 **진짜 마크업**을 쓰면 셋 다 해결된다.
 *
 * ## 지어내지 않는다
 *
 * 여기 숫자와 문구는 **우리 실측 보드의 실제 검사 결과 그대로다.**
 * XIAO 의 3.6V 는 Espressif 데이터시트 64쪽, 릴레이의 5V 는 자체 실측이다.
 * 홍보 화면이라고 없는 발견을 그려 넣지 않는다 (헌법 2-1).
 */
export function ReportPreview() {
  return (
    <figure
      aria-label="검사 결과 화면 미리보기"
      className="overflow-hidden rounded-card border border-line bg-surface shadow-card"
    >
      {/* 요약 — 실제 리포트의 01 절과 같은 값 */}
      <div className="grid grid-cols-3 divide-x divide-line border-b border-line">
        {[
          { label: "치명", value: "3", tone: "text-crit" },
          { label: "경고", value: "1", tone: "text-warn" },
          { label: "실행한 규칙", value: "15/15", tone: "text-ink" },
        ].map((t) => (
          <div key={t.label} className="px-4 py-3.5">
            <p className="text-[11px] font-bold text-mute">{t.label}</p>
            <p className={`mt-0.5 text-[22px] font-extrabold tracking-tight ${t.tone}`}>
              {t.value}
            </p>
          </div>
        ))}
      </div>

      {/* 발견 카드 하나 — 제품의 얼굴이다 */}
      <div className="px-5 py-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="rounded-chip bg-crit-weak px-2 py-0.5 text-[11px] font-bold text-crit">
            치명
          </span>
          <span className="data text-[12px] text-mute">R04</span>
          <span className="text-[15px] font-bold">
            외부 부품 출력이 GPIO 입력 최대 정격 초과
          </span>
        </div>

        <p className="mb-4 text-[14px] leading-relaxed text-sub">
          K1(JQC-3FF-S-Z)의 IO 로직 레벨은{" "}
          <strong className="font-bold text-ink">5V</strong>인데, 같은 네트에 물린
          U1(XIAO-ESP32C6)가 견디는 절대 최대 입력은{" "}
          <strong className="font-bold text-ink">3.6V</strong>입니다. 1.4V 초과입니다.
        </p>

        {/* 근거 레인 — 세로축은 "누가 말했는가" 하나만 뜻한다 (헌법 4절) */}
        <dl className="space-y-3 text-[13px]">
          <Lane label="회로도가 아는 것" state="읽음">
            <span className="data text-sub">
              K1.pad- → _IN_ACTIVE_LOW
              <br />
              U1.SDIO → _IN_ACTIVE_LOW
            </span>
          </Lane>
          <Lane label="부품이 아는 것" state="읽음">
            <span className="text-sub">
              Input power pins · Allowed input voltage −0.3 ~ 3.6 V
              <br />
              <span className="text-[12px] text-mute">
                Table 5-1. Absolute Maximum Ratings · p.64
              </span>
            </span>
          </Lane>
        </dl>

        <p className="mt-4 border-t border-line pt-3 text-[13px] leading-relaxed text-sub">
          <strong className="font-bold text-ink">다음 단계</strong> — 레벨 시프터나
          분압으로 3.6V 이하로 낮추세요. 절대 최대 정격을 넘으면 U1이 파손됩니다.
        </p>
      </div>
    </figure>
  );
}

/** 근거 한 줄. 리포트의 발견 카드와 같은 기호를 쓴다 — 사용자가 한 번만 배우면 된다 */
function Lane({
  label,
  state,
  children,
}: {
  label: string;
  state: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex gap-3">
      {/* 마디는 장식이라 낭독기에서 뺀다. 상태는 옆의 글자가 말한다 */}
      <span aria-hidden className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-ink" />
      <div className="min-w-0 flex-1">
        <dt className="mb-1 flex items-baseline gap-2">
          <span className="text-[13px] font-bold">{label}</span>
          <span className="text-[11px] text-mute">{state}</span>
        </dt>
        <dd className="overflow-x-auto rounded-block bg-surface-2 px-3 py-2 leading-relaxed">
          {children}
        </dd>
      </div>
    </div>
  );
}
