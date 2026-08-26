import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Header } from "../components/Layout";
import {
  ApiFailure,
  connectStartUrl,
  fetchRepos,
  type GithubRepo,
  type RepoScan,
  type ScanGroup,
  scanRepo,
  setupRepo,
} from "../lib/api";
import { useSession } from "../lib/session";

/**
 * 저장소 연동 — CI 설정 네 단계를 세 번의 클릭으로.
 *
 * ## 지금까지 사람들이 어디서 막혔나
 *
 *     ① 키 만들기       화면에 있다
 *     ② 시크릿 넣기     gh 명령 한 줄
 *     ③ YAML 쓰기       복사하면 된다
 *     ④ **경로 맞추기**  ← 여기서 제일 많이 틀린다
 *
 * ④를 우리가 대신한다. 저장소를 훑어 넷리스트·펌웨어·부품목록을 찾아
 * 경로가 채워진 워크플로 파일을 PR 로 올린다.
 *
 * ## 이 화면이 절대 하면 안 되는 것
 *
 * **틀린 경로를 자신 있게 채워 두는 것.** 액션이 "넷리스트를 못 찾았습니다"
 * 로 죽으면 사용자는 우리 도구가 고장 났다고 읽는다 — 자기가 고를 기회조차
 * 없었기 때문이다.
 *
 * 그래서 서버가 `picked: null` 을 주면 **칸을 비워 둔다.** 채워 넣지 않는다.
 * 채워 둔 값에도 「왜 이걸 골랐는지」를 항상 같이 보여준다 (헌법 2-1·2-3).
 *
 * ## 시크릿은 우리가 안 넣는다
 *
 * 넣으려면 저장소의 **모든 비밀값을 바꿀 수 있는 권한**을 받아야 한다.
 * 그 권한은 안 받는 편이 맞다고 봤고, 그 사실을 화면에 적는다.
 */
export function ConnectPage() {
  const { user, github, loading } = useSession();

  const [repos, setRepos] = useState<GithubRepo[] | null>(null);
  const [chosen, setChosen] = useState<GithubRepo | null>(null);
  const [scan, setScan] = useState<RepoScan | null>(null);
  const [paths, setPaths] = useState({ netlist: "", firmware: "", bom: "" });
  const [made, setMade] = useState<{ pull_request: string; path: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** 권한을 받아 돌아왔는지는 **목록을 실제로 불러 봐야** 안다. */
  const load = useCallback(async () => {
    try {
      setRepos(await fetchRepos());
    } catch {
      setRepos([]);
    }
  }, []);

  useEffect(() => {
    if (user) void load();
  }, [user, load]);

  async function pick(repo: GithubRepo) {
    setChosen(repo);
    setScan(null);
    setMade(null);
    setError(null);
    setBusy(true);
    try {
      const got = await scanRepo(repo.full_name, repo.default_branch);
      setScan(got);
      // **확신이 있는 것만 채운다.** 나머지는 빈칸으로 두고 사용자가 고르게 한다.
      setPaths({
        netlist: got.netlist.picked ?? "",
        firmware: got.firmware.picked ?? "",
        bom: got.bom.picked ?? "",
      });
    } catch (failure) {
      setError(failure instanceof ApiFailure ? failure.message : "저장소를 읽지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (!chosen) return;
    setBusy(true);
    setError(null);
    try {
      setMade(
        await setupRepo({
          repo: chosen.full_name,
          branch: chosen.default_branch,
          netlist: paths.netlist,
          firmware: paths.firmware || undefined,
          bom: paths.bom || undefined,
        })
      );
    } catch (failure) {
      setError(failure instanceof ApiFailure ? failure.message : "PR 을 만들지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Shell><p className="text-[15px] text-mute">불러오는 중…</p></Shell>;

  if (!user) {
    return (
      <Shell>
        <h1 className="mb-3 text-[26px] font-extrabold tracking-tight">저장소 연결</h1>
        <p className="mb-6 text-[15px] leading-relaxed text-sub">
          먼저 로그인해 주세요.
        </p>
        <Link to="/login" className="btn-primary">로그인</Link>
      </Shell>
    );
  }

  // 서버에 GitHub 앱이 없으면 이 화면 자체가 성립하지 않는다.
  if (github && !github.enabled) {
    return (
      <Shell>
        <h1 className="mb-3 text-[26px] font-extrabold tracking-tight">저장소 연결</h1>
        <p className="text-[15px] leading-relaxed text-sub">
          이 서버에는 GitHub 연동이 설정되어 있지 않습니다.
        </p>
      </Shell>
    );
  }

  const start = connectStartUrl();

  return (
    <Shell>
      <h1 className="mb-2 text-[26px] font-extrabold tracking-tight md:text-[30px]">
        저장소 연결
      </h1>
      <p className="mb-8 max-w-2xl text-[15px] leading-relaxed text-sub">
        저장소를 고르면 회로도·펌웨어·부품 목록이 어디 있는지 찾아서,{" "}
        <strong className="font-bold text-ink">경로가 채워진 워크플로 파일을 PR 로 올려 드립니다.</strong>{" "}
        머지하면 그때부터 PR 마다 검사가 돕니다.
      </p>

      {error && (
        <p role="alert" className="mb-6 rounded-block border border-crit/20 bg-crit-weak px-4 py-3 text-[14px] leading-relaxed text-ink">
          {error}
        </p>
      )}

      {made ? (
        <Done made={made} repo={chosen?.full_name ?? ""} />
      ) : repos === null ? (
        <p className="text-[15px] text-mute">불러오는 중…</p>
      ) : repos.length === 0 ? (
        <Grant href={start} />
      ) : (
        <>
          <Step n={1} title="저장소 고르기" />
          <ul className="mb-10 max-h-[320px] space-y-2 overflow-y-auto">
            {repos.map((repo) => (
              <li key={repo.full_name}>
                <button
                  type="button"
                  onClick={() => void pick(repo)}
                  className={`flex w-full items-center gap-3 rounded-card border px-5 py-3.5 text-left transition ${
                    chosen?.full_name === repo.full_name
                      ? "border-brand bg-brand/5"
                      : "border-line bg-surface hover:bg-surface-2"
                  }`}
                >
                  <span className="min-w-0 flex-1 truncate text-[15px] font-bold text-ink">
                    {repo.full_name}
                  </span>
                  {repo.private && (
                    <span className="shrink-0 rounded-chip bg-surface-2 px-2 py-1 text-[12px] font-bold text-mute">
                      비공개
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>

          {busy && !scan && <p className="text-[15px] text-mute">저장소를 훑는 중…</p>}

          {scan && (
            <>
              <Step n={2} title="파일 확인하기" />
              {/*
                **다 못 봤으면 말한다.** 이걸 숨기면 "넷리스트가 없습니다" 가 거짓이 된다.
              */}
              {scan.truncated && (
                <p className="mb-5 rounded-block border border-warn/25 bg-warn-weak px-4 py-3 text-[13.5px] leading-relaxed text-sub">
                  저장소가 커서 파일 {scan.files_seen}개까지만 봤습니다.{" "}
                  <strong className="font-bold text-ink">아래에 없다고 해서 없는 것은 아닙니다.</strong>{" "}
                  경로를 직접 적으셔도 됩니다.
                </p>
              )}

              <Slot
                label="회로도 넷리스트"
                required
                group={scan.netlist}
                value={paths.netlist}
                onChange={(v) => setPaths((p) => ({ ...p, netlist: v }))}
                missing="넷리스트가 없으면 검사를 시작할 수 없습니다."
              />
              <Slot
                label="펌웨어 폴더"
                group={scan.firmware}
                value={paths.firmware}
                onChange={(v) => setPaths((p) => ({ ...p, firmware: v }))}
                missing="비워 두면 코드 대조 규칙이 안 돕니다."
              />
              <Slot
                label="부품 목록 (BOM)"
                group={scan.bom}
                value={paths.bom}
                onChange={(v) => setPaths((p) => ({ ...p, bom: v }))}
                missing="비워 두면 부품 식별이 안 되고 오탐이 늘어납니다."
              />

              <Step n={3} title="PR 만들기" />
              <p className="mb-5 text-[14px] leading-relaxed text-sub">
                {/*
                  **되돌릴 수 있는 형태로 준다.** 기본 브랜치에 곧바로 커밋하면
                  마음에 안 들어도 이미 들어간 뒤다.
                */}
                기본 브랜치에 바로 쓰지 않고 <strong className="font-bold text-ink">PR 로 올립니다.</strong>{" "}
                내용을 보고 닫으셔도 됩니다.
              </p>
              <button
                type="button"
                onClick={() => void submit()}
                disabled={busy || !paths.netlist}
                className="btn-primary disabled:opacity-50"
              >
                {busy ? "만드는 중…" : "PR 만들기"}
              </button>
              {!paths.netlist && (
                <p className="mt-3 text-[13.5px] text-warn">넷리스트 경로를 정해 주세요.</p>
              )}
            </>
          )}
        </>
      )}
    </Shell>
  );
}

/** 아직 저장소 권한이 없을 때. **로그인과 다른 권한이라는 걸 미리 말한다.** */
function Grant({ href }: { href: string | null }) {
  return (
    <div className="rounded-card border border-line bg-surface p-7">
      <p className="mb-2 text-[16px] font-extrabold text-ink">저장소 접근을 허용해 주세요</p>
      <p className="mb-6 text-[14.5px] leading-relaxed text-sub">
        로그인할 때는 이름과 이메일만 받았습니다. 저장소를 훑고 PR 을 올리려면{" "}
        <strong className="font-bold text-ink">권한을 따로 받아야 합니다.</strong>
      </p>
      {href && <a href={href} className="btn-primary">GitHub에서 허용하기</a>}
      <p className="mt-5 text-[13px] leading-relaxed text-mute">
        받은 권한은 <strong className="font-semibold text-sub">이 연결 과정에서만 씁니다.</strong>{" "}
        저희 서버에 저장하지 않고, PR 을 만들고 나면 바로 버립니다.
      </p>
    </div>
  );
}

/**
 * 파일 슬롯 하나.
 *
 * **후보를 근거와 함께 늘어놓는다.** 근거가 없으면 사용자는 우리 추천을
 * 검증할 방법이 없고, 그러면 틀렸을 때 자기가 고를 기회 없이 당한다.
 */
function Slot({
  label,
  group,
  value,
  onChange,
  missing,
  required,
}: {
  label: string;
  group: ScanGroup;
  value: string;
  onChange: (v: string) => void;
  missing: string;
  required?: boolean;
}) {
  const guessed = group.picked === null && group.candidates.length > 0;

  return (
    <div className="mb-6 rounded-card border border-line bg-surface p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <p className="text-[15px] font-bold text-ink">{label}</p>
        <span className="rounded-chip bg-surface-2 px-2 py-0.5 text-[12px] font-bold text-mute">
          {required ? "필수" : "선택"}
        </span>
      </div>

      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={required ? "경로를 적어 주세요" : "없으면 비워 두세요"}
        className="mb-3 w-full rounded-block border border-line bg-bg px-4 py-2.5 font-mono text-[13.5px] outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20"
      />

      {/*
        **「우리가 골랐다」와 「고르지 못했다」를 구분해서 말한다.**
        후보는 있는데 확신이 없어서 비워 둔 경우가 가장 헷갈리는 자리다.
      */}
      {guessed && (
        <p className="mb-3 text-[13px] leading-relaxed text-warn">
          후보가 여럿이라 저희가 고르지 않았습니다. 아래에서 골라 주세요.
        </p>
      )}
      {group.candidates.length === 0 && (
        <p className="mb-1 text-[13px] text-mute">찾지 못했습니다. {missing}</p>
      )}

      {group.candidates.length > 0 && (
        <ul className="space-y-1.5">
          {group.candidates.map((c) => (
            <li key={c.path}>
              <button
                type="button"
                onClick={() => onChange(c.path)}
                className={`flex w-full flex-wrap items-baseline gap-x-3 gap-y-1 rounded-block px-3 py-2 text-left transition ${
                  value === c.path ? "bg-brand/5" : "hover:bg-surface-2"
                }`}
              >
                <code className="font-mono text-[13px] font-bold text-ink">{c.path}</code>
                <span className="text-[12.5px] text-mute">{c.reason}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** 다 됐을 때. **아직 하나 남았다는 걸 분명히 말한다.** */
function Done({ made, repo }: { made: { pull_request: string; path: string }; repo: string }) {
  // **주소를 지어내지 않는다.** 배포마다 다르므로 화면이 쓰는 값을 그대로 보여준다.
  const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
  return (
    <div className="rounded-card border border-ok/30 bg-ok-weak p-7">
      <p className="mb-2 text-[17px] font-extrabold text-ink">
        {repo} 에 PR 을 만들었습니다
      </p>
      <p className="mb-6 text-[14.5px] leading-relaxed text-sub">
        <code className="font-mono text-[13.5px]">{made.path}</code> 하나가 추가됩니다.
      </p>
      <a href={made.pull_request} target="_blank" rel="noreferrer" className="btn-primary">
        PR 열어 보기
      </a>

      {/*
        **끝났다고 말하지 않는다.** 시크릿이 없으면 액션이 401 로 죽고,
        사용자는 우리가 만들어 준 파일이 고장 났다고 읽는다 (헌법 2-4).
      */}
      {/*
        **배지는 덤이지만 눈에 띄어야 한다.** 남의 README 에 우리 이름이 박히는
        유일한 자리이고, 안 알려주면 아무도 안 쓴다.
      */}
      <div className="mt-7 border-t border-ok/20 pt-6">
        <p className="mb-2 text-[15px] font-bold text-ink">README 에 배지를 붙이시겠어요?</p>
        <p className="mb-3 text-[14px] leading-relaxed text-sub">
          최근 검사 결과가 저장소 첫 화면에 뜹니다. 치명이 있으면 빨간색입니다.
        </p>
        <code className="block overflow-x-auto rounded-block bg-surface px-4 py-3 font-mono text-[12.5px] text-ink">
          {`![Prefab](${apiBase}/api/v1/checks/<검사 ID>/badge.svg)`}
        </code>
      </div>

      <div className="mt-7 border-t border-ok/20 pt-6">
        <p className="mb-2 text-[15px] font-bold text-ink">머지 전에 하나 더 하셔야 합니다</p>
        <p className="mb-4 text-[14px] leading-relaxed text-sub">
          저장소에 <code className="font-mono text-[13px] font-bold">PREFAB_API_KEY</code> 시크릿을
          넣어 주세요. 키는{" "}
          <Link to="/mine" className="font-bold text-brand-strong hover:underline">
            내 검사
          </Link>{" "}
          화면에서 만듭니다.
        </p>
        <p className="text-[13px] leading-relaxed text-mute">
          <strong className="font-semibold text-sub">저희가 대신 넣지 않습니다.</strong>{" "}
          시크릿을 쓰는 권한까지 받으면 이 앱이 저장소의 모든 비밀값을 바꿀 수 있게 됩니다.
        </p>
      </div>
    </div>
  );
}

function Step({ n, title }: { n: number; title: string }) {
  return (
    <div className="mb-4 flex items-center gap-2.5">
      <span className="flex h-6 w-6 items-center justify-center rounded-chip bg-ink text-[12px] font-extrabold text-white">
        {n}
      </span>
      <h2 className="text-[17px] font-extrabold tracking-tight text-ink">{title}</h2>
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-2xl px-5 py-14 md:py-20">{children}</main>
    </div>
  );
}
