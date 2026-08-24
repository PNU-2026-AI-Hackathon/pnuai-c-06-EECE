import { Link } from "react-router-dom";

import { Header } from "../components/Layout";

/**
 * 데이터 처리 안내.
 *
 * **약관이 아니다.** 우리는 법률 문서를 쓸 수 없고, 쓰면 그게 거짓이 된다.
 * 여기 있는 것은 **코드가 실제로 하는 일**뿐이다 — 확인하려면 저장소를 열어 보면 된다.
 *
 * 이 화면이 필요한 이유는 분명하다. 이 도구는 **남의 회로도와 펌웨어**를 받는다.
 * 지적재산이다. 무엇을 저장하고 무엇을 안 저장하는지 말하지 않는 도구에
 * 그런 파일을 올릴 사람은 없다.
 */
export function PrivacyPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-3xl px-5 py-14 md:py-20">
        <h1 className="mb-3 text-[28px] font-extrabold leading-snug md:text-[36px]">
          올리신 파일을 어떻게 다루는지
        </h1>
        <p className="mb-10 text-[16px] leading-relaxed text-sub">
          이 도구는 회로도와 펌웨어를 받습니다. 남에게 보여주기 어려운
          파일이라는 것을 압니다. 그래서{" "}
          <strong className="font-bold text-ink">코드가 실제로 하는 일</strong>
          만 적습니다.
        </p>

        <Item
          head="업로드한 파일은 저장하지 않습니다"
          body="넷리스트·부품 목록·펌웨어는 메모리에서 읽어 검사한 뒤 버립니다. 디스크에 쓰지 않습니다."
        />
        <Item
          head="저장하는 것은 검사 결과입니다"
          body={
            <>
              결과에는{" "}
              <strong className="font-bold text-ink">
                근거로 인용된 코드 줄
              </strong>
              과 <strong className="font-bold text-ink">네트·부품 이름</strong>
              이 들어갑니다. 판정마다 어디를 보고 그렇게 말했는지 확인하실 수
              있어야 하기 때문입니다. 파일 전체가 아니라 인용된 부분입니다.
            </>
          }
        />
        <Item
          head="서버가 다시 뜨면 결과도 계정도 사라집니다"
          tone="warn"
          body="영구 저장 장치를 쓰지 않습니다. 배포하거나 서버가 재시작되면 그동안의 검사 결과와 계정이 함께 지워집니다. 남겨야 할 결과는 따로 저장해 두세요. 저장소가 재시작을 견디는 것이 실제로 확인되면 이 문구를 고치겠습니다."
        />
        <Item
          head="결과 주소를 아는 사람은 볼 수 있습니다"
          tone="warn"
          body={
            <>
              검사 결과 주소는 추측할 수 없는 무작위 값이지만,{" "}
              <strong className="font-bold text-ink">
                그 주소를 받은 사람은 누구나 열 수 있습니다.
              </strong>{" "}
              공유하실 때 이 점을 고려해 주세요.
            </>
          }
        />
        <Item
          head="계정을 만드시면 이메일과 비밀번호를 받습니다"
          body={
            <>
              검사를 실행하려면 계정이 필요합니다. 받는 것은{" "}
              <strong className="font-bold text-ink">이메일 주소 하나</strong>와
              비밀번호뿐입니다. 이름·전화번호·소속은 받지 않습니다.
              <br />
              <br />
              비밀번호는 <span className="data">scrypt</span> 로 해싱해
              저장합니다. 원문은 저장하지 않고 저희도 볼 수 없습니다. 로그인
              상태는{" "}
              <strong className="font-bold text-ink">
                스크립트가 읽을 수 없는 쿠키
              </strong>
              로 유지하며, 그 값도 서버에는 해시로만 들어 있습니다.
              <br />
              <br />
              인증 메일을 보내지 않으므로 이메일은 신원 확인이 아니라
              이름표입니다.{" "}
              <strong className="font-bold text-ink">
                저희가 보내는 메일은 하나도 없습니다.
              </strong>
            </>
          }
        />
        <Item
          head="검사 결과는 「내 검사」에 남고, 직접 지우실 수 있습니다"
          body={
            <>
              만드신 검사는 계정에 묶여 「내 검사」에 쌓이고, 언제든 직접 내리실 수
              있습니다. 다만{" "}
              <strong className="font-bold text-ink">
                결과 주소를 아는 사람은 로그인 없이도 열 수 있습니다
              </strong>{" "}
              — 팀에 링크로 공유하라고 그렇게 만들었습니다. 링크를 받은 사람까지
              가입하게 하면 공유가 공유가 아니게 됩니다.
              <br />
              <br />
              주소를 아는 사람도 못 열게 하는 비공개 링크는 준비 중입니다. 없는 것을
              있는 척하지 않겠습니다.
            </>
          }
        />
        <Item
          head="비밀번호를 잊으면 되돌릴 방법이 없습니다"
          tone="warn"
          body="메일을 보낼 수단이 없어서 재설정 기능을 만들지 못했습니다. 있는 척하지 않겠습니다. 비밀번호 관리자에 저장해 두시길 권합니다."
        />
        <Item
          head="데이터시트 읽기에만 외부 모델을 씁니다"
          body="부품 데이터시트에서 전기적 사실을 뽑을 때만 외부 AI 모델을 부릅니다. 그때도 올리신 회로도나 펌웨어를 보내지 않습니다. 판정 자체는 서버 안의 규칙이 합니다."
        />

        <div className="mt-12 rounded-card border border-line bg-surface px-5 py-5">
          <h2 className="mb-2 text-[17px] font-bold">
            아직 정식 약관이 아닙니다
          </h2>
          <p className="text-[15px] leading-relaxed text-sub">
            이 문서는 지금 코드가 하는 일을 적은 것이고, 법률 문서가 아닙니다.
            정식 서비스로 운영하게 되면 이용약관과 개인정보처리방침을 따로
            갖추겠습니다. 그때까지는 이 안내가 사실과 다르지 않도록 유지합니다 —{" "}
            <a
              href="https://github.com/PNU-2026-AI-Hackathon/pnuai-c-06-EECE"
              className="font-bold text-brand-strong underline"
            >
              저장소를 열어 직접 확인하실 수 있습니다.
            </a>
          </p>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Link to="/" className="btn-ghost">
            처음으로
          </Link>
          <Link to="/check" className="btn-primary">
            검사하러 가기
          </Link>
        </div>
      </main>
    </div>
  );
}

function Item({
  head,
  body,
  tone = "plain",
}: {
  head: string;
  body: React.ReactNode;
  tone?: "plain" | "warn";
}) {
  return (
    <section className="mb-8 border-t border-line pt-6">
      <h2
        className={`mb-2 text-[18px] font-bold ${tone === "warn" ? "text-warn" : ""}`}
      >
        {head}
      </h2>
      <p className="text-[15px] leading-relaxed text-sub">{body}</p>
    </section>
  );
}
