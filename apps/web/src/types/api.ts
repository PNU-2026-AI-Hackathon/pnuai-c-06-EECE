/**
 * API_CONTRACT.md 를 그대로 옮긴 것. 화면에서 임의로 변형하지 않는다.
 * 계약에 없는 필드를 여기에 추가하지 않는다 — 필요하면 백엔드 담당과 계약을 먼저 고친다.
 */

export type CheckStatus = "running" | "done" | "failed";
export type StepStatus = "done" | "partial" | "skipped" | "failed";
export type Severity = "CRITICAL" | "WARNING" | "INFO";
export type Verdict = "FAIL" | "PASS" | "UNRESOLVED";
export type Tier = "기본" | "차별";
export type EvidenceKind = "netlist" | "firmware" | "datasheet";

/** 넷리스트에서 읽은 근거 */
export interface NetlistEvidence {
  kind: "netlist";
  text: string;
  /** 강조 표시할 토큰 */
  highlight?: string[];
}

/**
 * 펌웨어 소스에서 읽은 근거.
 *
 * `line`이 `null`이면 **부재가 근거인 경우**다 — R8처럼 "코드를 다 읽었는데 이 핀이
 * 어디에도 없다"가 판정의 핵심일 때. 없는 줄 번호를 지어내지 않기 위해 비운다.
 */
export interface FirmwareEvidence {
  kind: "firmware";
  file: string;
  line: number | null;
  snippet: string;
  highlight?: string[];
}

/**
 * 부품 데이터시트에서 읽은 근거.
 *
 * `page`가 `null`이면 **실측이 근거인 경우**다 — 데이터시트가 없거나 그 항목을
 * 안 싣는 부품을 직접 재서 얻은 값. 없는 쪽 번호를 지어내지 않기 위해 비운다.
 */
export interface DatasheetEvidence {
  kind: "datasheet";
  mpn: string;
  table: string;
  page: number | null;
  quote: string;
  highlight?: string[];
}

export type Evidence = NetlistEvidence | FirmwareEvidence | DatasheetEvidence;

export interface Finding {
  /** 규칙 ID (예: "R12") */
  rule: string;
  title: string;
  tier: Tier;
  severity: Severity;
  verdict: Verdict;
  /** 대상 네트 이름. 네트와 무관한 발견이면 null */
  net: string | null;
  /** 무엇이 어긋났는지 한 문장 */
  claim: string;
  evidence: Evidence[];
  /** 다음에 무엇을 하면 되는지 */
  suggestion: string | null;
  /** 판정을 못 내린 이유. 판정했으면 null */
  unresolved_reason: string | null;
}

export interface PipelineStep {
  step: number;
  name: string;
  status: StepStatus;
  /** 무엇을 했는지 또는 왜 못 했는지 */
  detail: string | null;
}

export interface CheckSummary {
  critical: number;
  warning: number;
  /** 결함이 아니라 확인 요청. 세지 않으면 타일 합이 발견 수와 어긋난다 */
  info: number;
  cleared: number;
  rules_run: number;
  rules_skipped: number;
  /**
   * 카탈로그 전체 규칙 수. `rules_run + rules_skipped == rules_total` 이 항상 성립한다
   * (계약이 보장한다). 그래도 이 값을 직접 쓴다 — 합으로 계산하면 백엔드가
   * "후보에도 안 든 규칙"을 도입하는 순간 조용히 틀린다.
   */
  rules_total: number;
  parts_identified: number;
  parts_total: number;
}

export interface InputFile {
  filename: string;
  nets?: number;
  parts?: number;
  /** 펌웨어 zip 안에서 읽은 파일 수 */
  files?: number;
}

export interface CheckInputs {
  netlist: InputFile | null;
  bom: InputFile | null;
  firmware: InputFile | null;
}

/**
 * 확정된 패드 하나.
 *
 * `pin` 은 넷리스트에 **적힌** 이름이고 4자에서 잘려 있다 (`SDIO`).
 * `silk` · `gpio` 는 좌표로 **추론한** 신원이다 (`D5` · 23).
 * 모듈을 못 알아본 패드에는 둘 다 없다 — 그때는 `pin` 만 쓴다. 지어내지 않는다.
 */
export interface PadIdentity {
  /** 보드 실크 라벨 */
  silk?: string;
  /** 칩 GPIO 번호. 전원·접지 헤더 핀에는 없다 */
  gpio?: number;
}

export interface NetConnection extends PadIdentity {
  ref: string;
  pin: string;
}

/** `parts[].pads` — 이름이 뭉치기 전의 패드. 확정된 것만 실린다 */
export interface PartPad extends PadIdentity {
  pin: string;
}

export interface Net {
  name: string;
  vias: number;
  connections: NetConnection[];
}

export interface Part {
  ref: string;
  /** 넷리스트에 적힌 핀 이름. 4자에서 잘려 서로 뭉쳐 있다 */
  pins: string[];
  /** 제조사 부품번호. BOM이 없으면 null */
  mpn: string | null;
  /** 실크·GPIO 가 확정된 패드. 모듈을 못 알아봤으면 아예 없다 (빈 배열이 아니다) */
  pads?: PartPad[];
}

export interface CheckResult {
  check_id: string;
  status: CheckStatus;
  created_at: string;
  inputs: CheckInputs;
  summary: CheckSummary;
  pipeline: PipelineStep[];
  findings: Finding[];
  netlist: { nets: Net[]; parts: Part[] };
  /** 규칙 후보. 발견 루프를 안 돌렸으면 없다 */
  discovery?: Discovery;
  /**
   * 공개 범위. `link` 면 주소를 아는 누구나, `private` 면 주인만 열린다.
   *
   * **payload 가 아니라 서버 칼럼에서 온다.** 검사한 순간의 판정 기록과 달리
   * 주인이 언제든 바꾸는 값이라 섞으면 안 된다.
   *
   * 옛 목 파일에는 없을 수 있어 선택으로 둔다 — 없으면 `link` 로 본다.
   */
  visibility?: Visibility;
  /**
   * 지금 보는 사람이 주인인가. **공개 범위를 바꾸는 버튼은 이게 참일 때만 뜬다.**
   * 옛 목 파일에는 없어서 선택이고, 없으면 주인이 아닌 것으로 본다.
   */
  owned?: boolean;
}

export type Visibility = "link" | "private";

/** POST /api/v1/checks 응답 */
export interface CheckCreated {
  check_id: string;
  status: CheckStatus;
}

export interface RuleInfo {
  id: string;
  title: string;
  tier: Tier;
  severity: Severity;
  /** 이 규칙을 돌리는 데 필요한 입력 */
  needs: ("netlist" | "bom" | "firmware")[];
  implemented: boolean;
}

/** 오류 응답 */
export interface ApiError {
  error: { code: string; message: string };
}


/**
 * 규칙 후보 — **발견이 아니다.**
 *
 * `Finding` 과 일부러 다르게 생겼다. `severity` 도 `verdict` 도 없다 —
 * 붙이면 화면에서 발견처럼 보인다 (`docs/API_CONTRACT.md` 「discovery」).
 */
export interface Citation {
  kind: "firmware" | "netlist";
  where: string;
  what: string | null;
  quote: string | null;
}

export interface Candidate {
  title: string;
  why: string;
  citations: Citation[];
  covered_by: string | null;
}

export interface Discovery {
  candidates: Candidate[];
  dropped: { title: string; reason: string }[];
  /** 모델을 **못** 불렀을 때만 찬다. 안 부른 것과 못 부른 것은 다르다 */
  unavailable: string | null;
  notes: string[];
}

/** API 키. **원문(`token`)은 만들 때 한 번만 온다** — 목록에는 없다. */
export interface ApiKey {
  id: string;
  label: string;
  created_at: string;
  /** 한 번도 안 쓰였으면 `null`. 「이 키 아직 쓰이나」를 사용자가 알아야 지울 수 있다 */
  last_used_at: string | null;
}
