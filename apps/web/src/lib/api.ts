import type { CheckCreated, CheckResult, RuleInfo } from "../types/api";

import sample from "../mocks/check.json";

/**
 * 백엔드가 없으면 목으로 돈다. 기다리지 않는다.
 * VITE_API_BASE 가 설정되면 자동으로 실제 API를 쓴다.
 */
const BASE = import.meta.env.VITE_API_BASE as string | undefined;

/** 목 데이터 — 실제 .d356 을 파서·규칙엔진에 돌린 결과다. 손으로 적은 숫자가 없다. */
export const sampleCheck = sample as unknown as CheckResult;

export const usingMock = !BASE;

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
    // 목이 아는 검사는 샘플 하나뿐이다. 모르는 id를 아는 척하지 않는다
    if (id !== sampleCheck.check_id) {
      throw new ApiFailure(
        "그런 검사가 없습니다. 처음 화면에서 다시 실행해 주세요.",
        "CHECK_NOT_FOUND"
      );
    }
    return sampleCheck;
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
