import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import type { CheckResult } from "../types/api";

/**
 * 리포트에서 결과를 **들고 나가는** 수단.
 *
 * 이게 없던 동안 리포트 화면의 조작 요소는 로고와 「로그인」 둘뿐이었다.
 * 그런데 데이터 처리 안내는 "서버가 다시 뜨면 결과가 사라집니다" 라고 말하고,
 * 요금 페이지는 「결과 링크 공유」를 무료 기능으로 팔고 있었다 —
 * **파는 기능이 화면에 없었다.** 사용자는 주소창을 긁거나 스크린샷을 찍었고,
 * 그 순간 "근거까지 열리는 링크" 라는 우리 최대 강점이 통째로 사라진다.
 *
 * 두 가지만 둔다. 인쇄·PDF 는 나중이다.
 *
 *   링크 복사      — 팀에 보내는 가장 흔한 행동
 *   JSON 내려받기  — 결과가 사라져도 사용자 손에 남는 유일한 사본
 *
 * JSON 을 고른 이유는 **서버 응답 그대로**라서다. 화면이 다시 조립한 요약본을
 * 주면 나중에 그 파일로 무엇을 못 하는지 설명해야 한다. 계약(API_CONTRACT.md)
 * 그대로면 CI 든 스크립트든 같은 것을 읽는다.
 */
export function ReportActions({ check }: { check: CheckResult }) {
  return (
    <div className="mb-8 flex flex-wrap items-center gap-2">
      <CopyLink />
      <DownloadJson check={check} />
    </div>
  );
}

/** 복사 결과를 말해 준다. 눌렀는데 아무 일도 안 일어나면 다시 누른다 */
function CopyLink() {
  const [state, setState] = useState<"idle" | "done" | "failed">("idle");
  const timer = useRef<number>();

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const copy = async () => {
    const url = window.location.href;
    let ok = false;

    // 1. 표준 경로. HTTPS 나 localhost 가 아니면 아예 없고, 있어도 권한이 거절될 수 있다.
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(url);
        ok = true;
      }
    } catch {
      ok = false;
    }

    // 2. **대체 경로.** 위가 막히는 경우가 실제로 흔하다 — 권한 거절, 구형 브라우저,
    //    사내망의 http 배포. 여기서 포기하면 사용자는 주소창을 직접 긁어야 한다.
    if (!ok) {
      try {
        const box = document.createElement("textarea");
        box.value = url;
        // 화면 밖으로 밀되 `display:none` 은 안 된다 — 선택이 안 잡힌다
        box.setAttribute("readonly", "");
        box.style.position = "fixed";
        box.style.top = "-9999px";
        document.body.appendChild(box);
        box.select();
        ok = document.execCommand("copy");
        box.remove();
      } catch {
        ok = false;
      }
    }

    setState(ok ? "done" : "failed");
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setState("idle"), 2400);
  };

  return (
    <div className="flex items-center gap-2">
      <button type="button" onClick={copy} className="btn-ghost min-h-[44px]">
        {state === "done" ? "복사했습니다" : "링크 복사"}
      </button>
      {/*
        실패를 삼키지 않는다. 클립보드 권한이 없는 브라우저가 실제로 있고,
        그때 사용자는 자기가 잘못 눌렀다고 생각한다.
      */}
      {state === "failed" && (
        <span role="alert" className="text-[13px] text-warn">
          복사하지 못했습니다 — 주소창의 주소를 직접 복사해 주세요.
        </span>
      )}
    </div>
  );
}

/**
 * 결과를 파일로 내린다.
 *
 * **서버를 다시 부르지 않는다.** 이미 화면에 있는 것과 다른 것을 주면
 * "화면과 파일이 다르다" 는 문의가 생긴다.
 */
function DownloadJson({ check }: { check: CheckResult }) {
  const save = () => {
    const board =
      check.inputs.netlist?.filename.replace(/\.[^.]+$/, "") ?? check.check_id;
    const blob = new Blob([JSON.stringify(check, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `prefab-${board}-${check.check_id.slice(0, 8)}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    // 안 지우면 탭이 살아 있는 동안 메모리에 남는다
    URL.revokeObjectURL(url);
  };

  return (
    <button type="button" onClick={save} className="btn-ghost min-h-[44px]">
      JSON 내려받기
    </button>
  );
}

/**
 * 리포트 맨 아래에서 **다음 행동**을 준다.
 *
 * 랜딩에서 제일 큰 버튼이 「예시 검사 결과 보기」인데, 그 화면에 내 파일로 넘어가는
 * 길이 없었다. 설득이 최고조인 자리에서 다음 단계가 사라지는 구조였다.
 */
export function ReportNext({ isSample }: { isSample: boolean }) {
  return (
    <div className="mt-10 rounded-card border border-line bg-surface px-5 py-6 sm:px-6">
      <p className="mb-1 text-[17px] font-extrabold">
        {isSample ? "이제 내 보드로 해보세요" : "회로도를 고치셨나요?"}
      </p>
      <p className="mb-5 text-[15px] leading-relaxed text-sub">
        {isSample
          ? "가입도 설치도 없습니다. 넷리스트 파일 하나면 시작합니다."
          : "고친 회로도를 다시 올리면 이 발견이 사라졌는지 바로 확인할 수 있습니다."}
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <Link to="/check" className="btn-primary">
          {isSample ? "내 파일로 검사하기" : "다시 검사하기"}
        </Link>
        {!isSample && (
          <Link
            to="/r/chk_sample01"
            className="inline-flex min-h-[44px] items-center rounded-block px-3 text-[15px] font-bold text-sub hover:text-ink"
          >
            예시 결과 보기
          </Link>
        )}
      </div>
    </div>
  );
}
