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

/** 펌웨어 소스에서 읽은 근거 */
export interface FirmwareEvidence {
  kind: "firmware";
  file: string;
  line: number;
  snippet: string;
  highlight?: string[];
}

/** 부품 데이터시트에서 읽은 근거 */
export interface DatasheetEvidence {
  kind: "datasheet";
  mpn: string;
  table: string;
  page: number;
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
  cleared: number;
  rules_run: number;
  rules_skipped: number;
  parts_identified: number;
  parts_total: number;
}

export interface InputFile {
  filename: string;
  nets?: number;
  parts?: number;
}

export interface CheckInputs {
  netlist: InputFile | null;
  bom: InputFile | null;
  firmware: InputFile | null;
}

export interface NetConnection {
  ref: string;
  pin: string;
}

export interface Net {
  name: string;
  vias: number;
  connections: NetConnection[];
}

export interface Part {
  ref: string;
  pins: string[];
  /** 제조사 부품번호. BOM이 없으면 null */
  mpn: string | null;
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
}

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
