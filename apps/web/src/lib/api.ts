import type { CheckCreated, CheckResult, RuleInfo } from "../types/api";

// 목표 응답은 docs/examples 에 있는 파일을 그대로 읽는다. 사본을 만들지 않는다 —
// 계약 예시가 두 벌이 되는 순간 한쪽은 반드시 거짓이 된다.
import spec from "../../../../docs/examples/check.target-with-firmware.json";
import sample from "../mocks/check.json";

/**
 * 백엔드가 없으면 목으로 돈다. 기다리지 않는다.
 * VITE_API_BASE 가 설정되면 자동으로 실제 API를 쓴다.
 */
const BASE = import.meta.env.VITE_API_BASE as string | undefined;

/** 목 데이터 — 실제 .d356 을 파서·규칙엔진에 돌린 결과다. 손으로 적은 숫자가 없다. */
export const sampleCheck = sample as unknown as CheckResult;

/**
 * 목표 응답 명세 — R7 · R8 이 구현된 뒤 응답이 어떤 모양이면 되는지 적어둔 파일.
 * **실제 검사 결과가 아니다.** 코드 레인이 채워진 리포트를 백엔드보다 먼저 보기 위한 것이고,
 * 화면은 이게 명세라는 사실을 반드시 말해야 한다 (`checkNotice`).
 */
export const specCheck = spec as unknown as CheckResult;

const MOCK_NOTICE =
  "이 리포트는 실제 검사 결과가 아니라 docs/examples/check.target-with-firmware.json 의 " +
  "목표 응답 명세를 그대로 렌더한 것입니다. 여기 숫자를 인용하지 마세요.";

const MOCKS = new Map<string, { result: CheckResult; notice: string | null }>([
  [sampleCheck.check_id, { result: sampleCheck, notice: null }],
  [specCheck.check_id, { result: specCheck, notice: MOCK_NOTICE }],
]);

export const usingMock = !BASE;

/**
 * 이 검사 결과가 실제 검사가 아니면 그 사실. 실제면 `null`.
 *
 * 계약(`CheckResult`)에 필드를 추가하지 않기 위해 따로 둔다 —
 * 백엔드가 붙으면 이 함수는 항상 `null`을 준다.
 */
export function checkNotice(id: string): string | null {
  if (BASE) return null;
  return MOCKS.get(id)?.notice ?? null;
}

/** 서버가 내려준 한국어 메시지를 그대로 들고 다닌다 */
export class ApiFailure extends Error {
  constructor(
    message: string,
    readonly code: string
  ) {
    super(message);
  }
}

async function unwrap(res: Response) {
  const body = await res.json().catch(() => null);
  if (res.ok) return body;
  throw new ApiFailure(
    body?.error?.message ?? "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.",
    body?.error?.code ?? "UNKNOWN"
  );
}

/** 검사 생성 */
export async function createCheck(files: {
  netlist: File;
  bom?: File | null;
  firmware?: File | null;
}): Promise<CheckCreated> {
  if (!BASE) {
    // 목 모드에서는 파일을 보내지 않고 샘플 결과로 바로 넘어간다
    return { check_id: sampleCheck.check_id, status: "running" };
  }

  const form = new FormData();
  form.append("netlist", files.netlist);
  if (files.bom) form.append("bom", files.bom);
  if (files.firmware) form.append("firmware", files.firmware);

  return unwrap(await fetch(`${BASE}/api/v1/checks`, { method: "POST", body: form }));
}

/** 결과 조회 */
export async function getCheck(id: string): Promise<CheckResult> {
  if (!BASE) {
    // 목이 아는 검사만 돌려준다. 모르는 id를 아는 척하지 않는다
    const hit = MOCKS.get(id);
    if (!hit) {
      throw new ApiFailure(
        "그런 검사가 없습니다. 처음 화면에서 다시 실행해 주세요.",
        "CHECK_NOT_FOUND"
      );
    }
    return hit.result;
  }
  return unwrap(await fetch(`${BASE}/api/v1/checks/${id}`));
}

/**
 * 규칙 카탈로그.
 *
 * 화면이 "규칙 몇 개가 못 돈다"를 말하려면 이 목록이 있어야 한다.
 * 목 모드에는 카탈로그가 없다 — 그래서 `null`을 준다.
 * **숫자를 지어내지 않기 위해서다.** 카탈로그가 없으면 화면은 개수를 말하지 않는다.
 */
export async function getRules(): Promise<RuleInfo[] | null> {
  if (!BASE) return null;
  const body = await unwrap(await fetch(`${BASE}/api/v1/rules`));
  return body?.rules ?? null;
}
