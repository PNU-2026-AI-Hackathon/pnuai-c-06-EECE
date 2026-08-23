import type { CheckCreated, CheckResult, RuleInfo } from "../types/api";

// 목표 응답은 docs/examples 에 있는 파일을 그대로 읽는다. 사본을 만들지 않는다 —
// 계약 예시가 두 벌이 되는 순간 한쪽은 반드시 거짓이 된다.
import spec from "../../../../docs/examples/check.target-with-firmware.json";
// **사본을 만들지 않는다.** 백엔드가 배포 서버에 싣는 바로 그 파일을 읽는다.
// 복사해 뒀더니 규칙 11개 시절 결과가 목 모드에 그대로 남아, 목과 서버가
// 같은 id(`chk_sample01`)로 **다른 숫자**를 보여줬다.
import sample from "../../../api/src/prefab/samples/check.sample.json";
import ruleCatalog from "../mocks/rules.json";

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
 * 로컬 개발인지 배포된 화면인지.
 * 서버에 못 닿았을 때 **사용자가 할 수 있는 일이 다르다** — 로컬이면 서버를 띄우면 되고,
 * 배포판이면 사용자가 할 수 있는 게 없다. 문구도 달라야 한다.
 */
const IS_LOCAL = !!BASE && /^https?:\/\/(localhost|127\.0\.0\.1)(:|\/|$)/.test(BASE);

const UNREACHABLE = IS_LOCAL
  ? "검사 서버에 연결하지 못했습니다. 서버가 실행 중인지 확인해 주세요."
  : "검사 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.";

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

/**
 * **서버가 거절한 것과 서버에 닿지도 못한 것은 다르다.**
 *
 * `fetch` 는 전자를 응답으로, 후자를 예외로 알린다. 둘을 한 문구로 합치면
 * 사용자는 자기 파일이 잘못된 건지 서버가 죽은 건지 구분할 수 없다.
 */
async function request(path: string, init?: RequestInit) {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { credentials: "include", ...init });
  } catch {
    throw new ApiFailure(UNREACHABLE, "NETWORK_UNREACHABLE");
  }
  return unwrap(res);
}

/**
 * `credentials: "include"` 를 **한 곳에서** 붙인다.
 *
 * 호출하는 쪽마다 적게 두면 반드시 한 군데를 빠뜨리고, 그러면 그 요청만
 * 로그아웃 상태로 간다. 증상이 고약하다 — 화면은 로그인돼 있는데 어떤
 * 버튼 하나만 "로그인이 필요합니다"라고 한다.
 */
async function send(path: string, body: unknown) {
  return request(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** 저장소가 재시작을 견디는지. `unknown` 은 **"안전"이 아니라 "모름"** 이다. */
export type StorageState = {
  state: "unknown" | "persistent";
  boots: number;
  first_seen: string | null;
  survives_restart: boolean;
};

export type Account = {
  email: string;
  created_at: string;
  storage: StorageState;
};

export type CheckSummaryRow = {
  check_id: string;
  created_at: string;
  summary: { critical: number; warning: number; info: number; cleared: number };
  netlist_filename: string | null;
};

export async function signup(email: string, password: string): Promise<Account> {
  return send("/api/v1/auth/signup", { email, password });
}

export async function login(email: string, password: string): Promise<Account> {
  return send("/api/v1/auth/login", { email, password });
}

export async function logout(): Promise<void> {
  await send("/api/v1/auth/logout", {});
}

/**
 * 로그인 상태. **로그아웃은 오류가 아니라 `null` 이다.**
 *
 * 화면이 뜨자마자 부르는 자리라, 로그아웃을 예외로 만들면 콘솔이 401 로
 * 가득 차고 진짜 오류가 그 사이에 묻힌다.
 */
export async function fetchMe(): Promise<{ user: Account | null; storage: StorageState } | null> {
  if (!BASE) return null;
  try {
    const res = await fetch(`${BASE}/api/v1/auth/me`, { credentials: "include" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchMyChecks(): Promise<CheckSummaryRow[]> {
  const body = await request("/api/v1/checks/mine");
  return body.checks ?? [];
}

export async function deleteCheck(id: string): Promise<void> {
  await request(`/api/v1/checks/${id}`, { method: "DELETE" });
}

/** 이 서버의 실측 사용량. 요금 안내 화면이 숫자를 손으로 안 적으려고 쓴다. */
export type Usage = {
  parts: number;
  facts: number;
  checks: number;
  cleared_by_facts: number;
  /** 사실 DB 를 만드느라 부른 횟수. 부품당 한 번, 검사와 무관하게 미리. */
  llm_calls_building_db: number;
  /** 검사를 처리하느라 부른 횟수. **구조적으로 0**. 서버가 그렇게 답한다. */
  llm_calls_serving_checks: number;
};

/**
 * **못 가져오면 `null` 이다. 0 이 아니다.**
 *
 * 0 으로 채우면 "부품 0개"라고 적힌 요금 안내가 뜬다 — 서버가 안 뜬 것과
 * DB 가 비어 있는 것은 다른 사실인데 화면에는 똑같이 보인다 (헌법 2-2).
 */
export async function fetchUsage(): Promise<Usage | null> {
  if (!BASE) return null;
  try {
    const res = await fetch(`${BASE}/api/v1/usage`);
    if (!res.ok) return null;
    return asUsage(await res.json());
  } catch {
    return null;
  }
}

/**
 * 모양이 맞는지 본 뒤에 돌려준다. 아니면 `null`.
 *
 * 안 보다가 한 번 당했다. 서버가 아직 옛 판이라 새 항목이 없었는데, 화면은
 * 그걸 `undefined` 로 받아 **"부른 AI 호출은 번입니다"** 라고 출력했다.
 * 숫자만 쏙 빠진 문장이 아무 경고 없이 떠 있었다.
 *
 * 배포가 갈리는 몇 초 동안만 생기는 일이지만, 조용히 틀린 문장을 띄우느니
 * 못 가져왔다고 말하는 편이 낫다 (헌법 2-3).
 */
function asUsage(body: unknown): Usage | null {
  if (!body || typeof body !== "object") return null;
  const fields = [
    "parts",
    "facts",
    "checks",
    "cleared_by_facts",
    "llm_calls_building_db",
    "llm_calls_serving_checks",
  ] as const;
  const row = body as Record<string, unknown>;
  for (const key of fields) {
    if (typeof row[key] !== "number" || !Number.isFinite(row[key])) return null;
  }
  return body as Usage;
}

/** 검사 생성 */
export async function createCheck(files: {
  netlist: File;
  bom?: File | null;
  firmware?: File | null;
  /** 바뀌기 전 회로도. 이게 있어야 R10(드리프트)이 돈다 */
  previousNetlist?: File | null;
}): Promise<CheckCreated> {
  if (!BASE) {
    // 목 모드에서는 파일을 보내지 않고 샘플 결과로 바로 넘어간다
    return { check_id: sampleCheck.check_id, status: "running" };
  }

  const form = new FormData();
  form.append("netlist", files.netlist);
  if (files.bom) form.append("bom", files.bom);
  if (files.firmware) form.append("firmware", files.firmware);
  if (files.previousNetlist) form.append("previous_netlist", files.previousNetlist);

  return request("/api/v1/checks", { method: "POST", body: form });
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
  return request(`/api/v1/checks/${id}`);
}

/**
 * 규칙 카탈로그.
 *
 * 화면이 "규칙 몇 개가 못 돈다"를 말하려면 이 목록이 있어야 한다.
 * 목 모드에서는 백엔드가 만들어 준 `mocks/rules.json` 을 읽는다 —
 * 손으로 적은 목록이 아니라 `catalog.py` 에서 뽑은 것이다.
 *
 * ```bash
 * cd apps/api && python -m prefab --rules-json > ../web/src/mocks/rules.json
 * ```
 */
export async function getRules(): Promise<RuleInfo[] | null> {
  if (!BASE) return (ruleCatalog as { rules: RuleInfo[] }).rules ?? null;
  try {
    const body = await request("/api/v1/rules");
    return body?.rules ?? null;
  } catch (e) {
    // 경로와 메서드는 개발자만 쓸 수 있는 정보다. 화면이 아니라 콘솔로 보낸다
    console.warn(`[prefab] GET ${BASE}/api/v1/rules 실패`, e);
    throw e;
  }
}
