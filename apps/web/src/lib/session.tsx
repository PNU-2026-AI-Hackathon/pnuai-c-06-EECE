import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  type Account,
  fetchMe,
  type GithubAuth,
  type GuestQuota,
  logout as apiLogout,
  type StorageState,
} from "./api";

/**
 * 로그인 상태를 화면 전체가 같이 본다.
 *
 * **로그아웃은 오류가 아니다.** 이 앱은 로그인 없이도 전부 돌아간다 —
 * 검사도 되고 결과 링크도 열린다 (헌법 4절 단서 1). 그래서 여기서 하는 일은
 * 문을 잠그는 게 아니라, 로그인했으면 **더 해 줄 수 있는 것**을 켜는 것뿐이다.
 */
type Session = {
  user: Account | null;
  storage: StorageState | null;
  /** 서버가 GitHub 로그인을 할 수 있는가. **모르는 동안은 `null` 이다** — 거짓이 아니다. */
  github: GithubAuth | null;
  /** 로그인 안 한 사람에게 남은 체험 횟수. 로그인했으면 뜻이 없다. */
  guest: GuestQuota | null;
  /** 아직 확인 중인가. 이걸 안 보면 새로고침마다 헤더가 "로그인"으로 깜빡인다. */
  loading: boolean;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
  setUser: (user: Account | null) => void;
};

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Account | null>(null);
  const [storage, setStorage] = useState<StorageState | null>(null);
  const [github, setGithub] = useState<GithubAuth | null>(null);
  const [guest, setGuest] = useState<GuestQuota | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const got = await fetchMe();
    setUser(got?.user ?? null);
    setStorage(got?.storage ?? null);
    setGithub(got?.github ?? null);
    setGuest(got?.guest ?? null);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signOut = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, storage, github, guest, loading, refresh, signOut, setUser }),
    [user, storage, github, guest, loading, refresh, signOut]
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const found = useContext(SessionContext);
  if (!found) throw new Error("SessionProvider 안에서만 쓸 수 있습니다");
  return found;
}
