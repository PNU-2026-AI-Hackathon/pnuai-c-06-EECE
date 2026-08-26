import type { ApiKey, CheckCreated, CheckResult, RuleInfo, Visibility } from "../types/api";

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

/**
 * 서버가 GitHub 로그인을 할 수 있는가.
 *
 * **버튼을 그릴지 정하는 유일한 근거다.** 서버에 GitHub 앱이 설정돼 있지
 * 않으면 눌러도 404 가 난다 — 그런 버튼을 화면에 두지 않는다 (헌법 2-2).
 */
export type GithubAuth = { enabled: boolean };

/**
 * 로그인 안 한 사람이 몇 번 더 써 볼 수 있는가.
 *
 * **화면이 이 숫자를 지어내면 안 된다.** 표는 httpOnly 쿠키라 브라우저 코드가
 * 못 읽는다 — 서버가 말해 주는 값만 쓴다.
 */
export type GuestQuota = { remaining: number; free: number };

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
export async function fetchMe(): Promise<{
  user: Account | null;
  storage: StorageState;
  github?: GithubAuth;
  guest?: GuestQuota;
} | null> {
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

/**
 * 출시 알림 대기 명단.
 *
 * **목 모드에서는 서버에 안 보낸다.** 백엔드 없이 화면만 띄운 상태에서 눌렀을 때
 * "등록했습니다" 라고 하면 그건 거짓말이다 — 아무 데도 안 갔다.
 */
export async function joinWaitlist(email: string, plan: "pro" | "team"): Promise<void> {
  if (!BASE) {
    throw new ApiFailure(
      "지금은 서버에 연결되어 있지 않아 등록하지 못했습니다.",
      "NO_BACKEND"
    );
  }
  await request("/api/v1/waitlist", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, plan }),
  });
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

/** 검사 하나의 공개 범위를 바꾼다. **주인만 된다** — 아니면 404. */
export async function setVisibility(
  id: string,
  visibility: Visibility
): Promise<{ check_id: string; visibility: Visibility }> {
  return send(`/api/v1/checks/${id}/visibility`, { visibility });
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

/**
 * API 키 목록. **원문은 안 온다** — 서버에도 해시만 있다.
 */
export async function fetchKeys(): Promise<{ keys: ApiKey[]; max: number }> {
  return request("/api/v1/keys");
}

/**
 * 키를 만든다. 돌려주는 `token` 은 **이때 한 번만** 존재한다.
 * 화면은 그 사실을 만들기 전에 말해야 한다.
 */
export async function createKey(label: string): Promise<ApiKey & { token: string }> {
  return send("/api/v1/keys", { label });
}

export async function revokeKey(id: string): Promise<void> {
  await request(`/api/v1/keys/${id}`, { method: "DELETE" });
}

/**
 * GitHub 승인 화면으로 가는 주소.
 *
 * **`fetch` 가 아니라 주소창으로 간다.** OAuth 는 사용자를 GitHub 으로 실제로
 * 보냈다가 데려오는 흐름이라, XHR 로는 성립하지 않는다. 그래서 `<a href>` 다.
 *
 * `BASE` 가 없으면(목 모드) `null` — 화면이 버튼을 안 그린다.
 */
export function githubStartUrl(next: string): string | null {
  return BASE ? `${BASE}/api/v1/auth/github/start?next=${encodeURIComponent(next)}` : null;
}

// --------------------------------------------------------- 저장소 연동

/** 저장소를 훑어 찾은 후보 하나. **왜 골랐는지 같이 온다.** */
export type FileCandidate = { path: string; score: number; reason: string };

/**
 * 한 종류(넷리스트·펌웨어·부품목록)의 결과.
 *
 * **`picked` 가 `null` 인 것은 "없다"가 아니라 "우리가 고를 만큼 확신이 없다"** 이다.
 * 그때 화면은 칸을 비워 두고 사용자가 고르게 한다 — 틀린 값을 채워 두면
 * 검토를 건너뛰게 되고, 액션이 엉뚱한 오류로 죽는다.
 */
export type ScanGroup = { picked: string | null; candidates: FileCandidate[] };

export type RepoScan = {
  repo: string;
  branch: string;
  files_seen: number;
  /** 저장소가 커서 다 못 봤는가. **숨기면 「없습니다」가 거짓이 된다.** */
  truncated: boolean;
  netlist: ScanGroup;
  firmware: ScanGroup;
  bom: ScanGroup;
};

export type GithubRepo = { full_name: string; private: boolean; default_branch: string };

export function connectStartUrl(): string | null {
  return BASE ? `${BASE}/api/v1/github/connect/start` : null;
}

export async function fetchRepos(): Promise<GithubRepo[]> {
  const got = (await request("/api/v1/github/repos")) as { repos: GithubRepo[] };
  return got.repos;
}

export async function scanRepo(repo: string, branch: string): Promise<RepoScan> {
  return (await request(
    `/api/v1/github/scan?repo=${encodeURIComponent(repo)}&branch=${encodeURIComponent(branch)}`
  )) as RepoScan;
}

export async function setupRepo(body: {
  repo: string;
  branch: string;
  netlist: string;
  firmware?: string;
  bom?: string;
}): Promise<{ pull_request: string; path: string }> {
  // `send` 가 POST + JSON + credentials 를 한 곳에서 붙인다.
  return (await send("/api/v1/github/setup", body)) as { pull_request: string; path: string };
}
