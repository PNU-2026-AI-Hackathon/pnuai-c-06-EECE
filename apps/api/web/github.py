"""GitHub 으로 로그인.

## 왜 붙이는가

우리에게 **비밀번호 재설정이 없다** (`auth.py` 「안 만든 것」). 메일 보낼 수단이
없어서 그렇고, 그래서 가입 화면에 "잊으면 되찾을 수 없습니다" 라고 적어 뒀다.
정직하지만 실서비스에서는 아픈 자리다.

GitHub 으로 들어오면 그 문제가 통째로 없어진다 — **비밀번호를 우리가 안 갖는다.**
개발자를 상대하는 제품이라 대상자는 거의 다 계정이 있고, CI 연동이 결국
GitHub 위에서 도는 것이라 신원도 같은 곳에서 오는 편이 자연스럽다.

## 켜지지 않았으면 없는 것이다

`GITHUB_CLIENT_ID` · `GITHUB_CLIENT_SECRET` 이 없으면 `enabled` 가 거짓이고,
화면은 버튼을 **아예 안 그린다.** 눌러도 안 되는 버튼을 두는 것이 헌법 2-4 위반이다.

## state 를 서명해서 들고 다닌다 (DB 에 안 넣는다)

CSRF 를 막으려면 "이 콜백이 우리가 시작한 것인가" 를 확인해야 한다. 보통은
서버에 nonce 를 저장해 두는데, **우리는 재배포마다 DB 가 날아간다.**
저장해 두면 배포 중에 로그인하던 사람이 전부 실패한다.

대신 **클라이언트 시크릿으로 HMAC 서명해서 state 에 실어 보낸다.** 돌아온 값의
서명을 검증하면 우리가 만든 것인지 알 수 있고, 저장소가 필요 없다.
유효기간을 같이 서명해서 재사용도 막는다.

## 계정을 잇는 규칙 — 여기서 틀리면 남의 계정을 준다

    1. github_id 로 찾는다               → 있으면 그 사람이다
    2. 없으면 **인증된** 이메일로 찾는다  → 있으면 잇는다
    3. 그래도 없으면 새로 만든다

**2번의 「인증된」이 이 파일에서 제일 중요한 단어다.** GitHub 은 확인 안 된
이메일도 계정에 달게 해 준다. 그걸 그대로 믿고 이으면, 아무나 `victim@x.com`
을 자기 GitHub 에 적어 두고 우리 쪽 그 계정을 가져갈 수 있다.
그래서 `verified: true` 인 주소만 본다.

**`github_id` 를 신원으로 쓴다. 로그인 이름(`login`)은 안 쓴다** — 사용자가
바꿀 수 있고, 남이 그 이름을 다시 차지할 수 있다. 숫자 id 는 안 바뀐다.
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from hashlib import sha256

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
API_USER = "https://api.github.com/user"
API_EMAILS = "https://api.github.com/user/emails"

#: 요청하는 권한. **신원만 본다.**
#:
#: 저장소를 읽을 생각이 없으므로 `repo` 를 안 넣는다. 로그인하려고 눌렀는데
#: "이 앱이 당신의 모든 저장소를 읽습니다" 라고 뜨면 거기서 그만둔다.
#: 나중에 저장소 연동을 붙이면 **그때 따로 물어본다.**
SCOPE = "read:user user:email"

#: state 유효기간. 사람이 GitHub 화면에서 승인하는 데 드는 시간 + 여유.
STATE_TTL_SECONDS = 600

#: 로그인 뒤 돌아갈 수 있는 화면. **여기 없는 곳으로는 안 보낸다.**
#:
#: `?next=` 를 그대로 믿으면 공격자가 우리 로그인 링크를 미끼로 남의 사이트에
#: 떨어뜨릴 수 있다 (오픈 리다이렉트). 경로 목록으로 못 박는다.
SAFE_NEXT = ("/mine", "/check", "/pricing", "/connect", "/")


class GithubError(Exception):
    """사용자에게 보여줄 수 있는 거절. `code` 는 화면이 문구를 고르는 데 쓴다."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Config:
    client_id: str
    client_secret: str
    #: GitHub 이 돌아올 곳. 우리 **API** 주소다 (화면 주소가 아니다) —
    #: 세션 쿠키를 API 도메인에 심어야 하기 때문이다.
    redirect_uri: str
    #: 다 끝나고 사람을 보낼 화면 주소.
    web_base: str

    @property
    def enabled(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)


def config_from_env() -> Config:
    return Config(
        client_id=os.getenv("GITHUB_CLIENT_ID", "").strip(),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET", "").strip(),
        redirect_uri=os.getenv("GITHUB_REDIRECT_URI", "").strip(),
        web_base=os.getenv("WEB_APP_URL", "https://prefab-web.onrender.com").rstrip("/"),
    )


@dataclass(frozen=True)
class Identity:
    """GitHub 이 말해 준 신원. **여기 있는 것이 우리가 아는 전부다.**"""

    github_id: int
    login: str
    #: **인증된** 주소만 들어온다. 못 찾으면 `None` 이고, 그러면 계정을 안 만든다.
    email: str | None


# ------------------------------------------------------------ 순수 함수

def safe_next(raw: str | None) -> str:
    """돌아갈 경로. **목록에 없으면 `/mine` 으로 보낸다.**"""
    return raw if raw in SAFE_NEXT else "/mine"


def sign_state(secret: str, nonce: str, expires_at: int) -> str:
    """`nonce.만료.서명`. 서버에 아무것도 안 남긴다."""
    payload = f"{nonce}.{expires_at}"
    mac = hmac.new(secret.encode(), payload.encode(), sha256).hexdigest()
    return f"{payload}.{mac}"


def new_state(secret: str, now: int | None = None) -> str:
    at = (now if now is not None else int(time.time())) + STATE_TTL_SECONDS
    return sign_state(secret, secrets.token_urlsafe(16), at)


def check_state(secret: str, raw: str | None, now: int | None = None) -> None:
    """우리가 만든 state 이고 아직 안 지났으면 조용히 돌아온다.

    **틀린 이유를 나눠서 말하지 않는다.** 위조인지 만료인지 알려 주면
    공격자가 어디까지 맞췄는지 알게 된다.
    """
    moment = now if now is not None else int(time.time())
    try:
        nonce, expires_raw, _ = (raw or "").split(".")
        expires_at = int(expires_raw)
    except ValueError:
        raise GithubError("BAD_STATE", "로그인 요청이 올바르지 않습니다. 다시 시도해 주세요.") from None

    if not hmac.compare_digest(sign_state(secret, nonce, expires_at), raw or ""):
        raise GithubError("BAD_STATE", "로그인 요청이 올바르지 않습니다. 다시 시도해 주세요.")
    if expires_at <= moment:
        raise GithubError("BAD_STATE", "로그인 요청이 올바르지 않습니다. 다시 시도해 주세요.")


def authorize_url(config: Config, state: str) -> str:
    """GitHub 승인 화면 주소. **순수 함수다.**"""
    query = urllib.parse.urlencode(
        {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "scope": SCOPE,
            "state": state,
            # 계정을 이미 승인한 사람도 매번 GitHub 을 거치게 둔다.
            "allow_signup": "true",
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


def pick_email(payload: list) -> str | None:
    """이메일 목록에서 **인증된** 주소 하나를 고른다.

    기본 주소를 먼저 보고, 그게 인증 전이면 인증된 다른 주소를 쓴다.
    하나도 없으면 `None` — **지어내지 않는다** (헌법 2-2).
    """
    entries = [e for e in payload if isinstance(e, dict)]
    verified = [e for e in entries if e.get("verified") and e.get("email")]
    for entry in verified:
        if entry.get("primary"):
            return str(entry["email"]).strip().lower()
    return str(verified[0]["email"]).strip().lower() if verified else None


# ------------------------------------------------------------ 네트워크

def _post_json(url: str, data: dict, timeout: int = 15) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read())


def _get_json(url: str, token: str, timeout: int = 15):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "prefab")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read())


def exchange_code(config: Config, code: str) -> str:
    """승인 코드를 접근 토큰으로 바꾼다.

    **GitHub 은 실패해도 HTTP 200 을 준다.** 본문에 `error` 를 담아서 온다 —
    상태 코드만 보면 빈 토큰을 들고 다음 단계로 간다.
    """
    try:
        payload = _post_json(
            TOKEN_URL,
            {
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "code": code,
                "redirect_uri": config.redirect_uri,
            },
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise GithubError("GITHUB_UNREACHABLE", "GitHub 에 닿지 못했습니다. 잠시 후 다시 시도해 주세요.") from exc

    token = str(payload.get("access_token") or "")
    if not token:
        raise GithubError("EXCHANGE_FAILED", "GitHub 로그인을 마치지 못했습니다. 다시 시도해 주세요.")
    return token


def fetch_identity(token: str) -> Identity:
    """누구인지 묻는다. 이메일은 **인증된 것만** 가져온다."""
    try:
        user = _get_json(API_USER, token)
        emails = _get_json(API_EMAILS, token)
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise GithubError("GITHUB_UNREACHABLE", "GitHub 에 닿지 못했습니다. 잠시 후 다시 시도해 주세요.") from exc

    github_id = user.get("id")
    if not isinstance(github_id, int):
        raise GithubError("EXCHANGE_FAILED", "GitHub 로그인을 마치지 못했습니다. 다시 시도해 주세요.")

    return Identity(
        github_id=github_id,
        login=str(user.get("login") or ""),
        email=pick_email(emails if isinstance(emails, list) else []),
    )


# --------------------------------------------------- 저장소 연동 (별도 권한)

#: 저장소를 읽고 워크플로 파일을 넣으려면 필요한 권한.
#:
#: **로그인과 일부러 나눠 놨다.** 로그인하려고 눌렀는데 "모든 저장소를 읽고
#: 씁니다" 가 뜨면 거기서 그만둔다. 저장소 연동을 누른 사람은 무엇을 하려는지
#: 알고 누른 것이라, 그때 물어보면 납득이 된다.
#:
#: `workflow` 가 따로 필요하다 — `repo` 만으로는 `.github/workflows/` 아래
#: 파일을 못 만든다. GitHub 이 그 폴더만 별도로 잠가 뒀다.
CONNECT_SCOPE = "repo workflow"

#: 한 번에 훑을 파일 수 상한.
#:
#: 저장소가 클 수 있다. 상한을 넘으면 **자르지 않고 잘렸다고 말한다** —
#: 조용히 자르면 "넷리스트가 없네요" 가 나오고, 사용자는 우리가 다 봤다고 믿는다.
MAX_TREE_FILES = 4000


@dataclass(frozen=True)
class Repo:
    full_name: str
    private: bool
    default_branch: str

    def to_dict(self) -> dict:
        return {
            "full_name": self.full_name,
            "private": self.private,
            "default_branch": self.default_branch,
        }


def connect_url(config: Config, state: str) -> str:
    """저장소 권한을 물어보는 승인 화면. 로그인과 **다른 scope** 를 쓴다."""
    query = urllib.parse.urlencode(
        {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "scope": CONNECT_SCOPE,
            "state": state,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


def list_repos(token: str, limit: int = 100) -> list[Repo]:
    """쓸 수 있는 저장소. **`push` 권한이 있는 것만** 보여준다.

    읽기만 되는 저장소를 목록에 넣으면, 골라 놓고 마지막에 "권한이 없습니다"
    로 막힌다. 고르기 전에 거르는 편이 낫다.
    """
    url = f"https://api.github.com/user/repos?per_page={limit}&sort=pushed&affiliation=owner,collaborator,organization_member"
    try:
        payload = _get_json(url, token)
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise GithubError("GITHUB_UNREACHABLE", "GitHub 에 닿지 못했습니다. 잠시 후 다시 시도해 주세요.") from exc

    found = []
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict) or not (item.get("permissions") or {}).get("push"):
            continue
        found.append(
            Repo(
                full_name=str(item.get("full_name") or ""),
                private=bool(item.get("private")),
                default_branch=str(item.get("default_branch") or "main"),
            )
        )
    return found


def list_paths(token: str, full_name: str, branch: str) -> tuple[list[str], bool]:
    """저장소의 파일 경로 전부. `(경로들, 잘렸는가)`.

    **잘렸는지를 같이 돌려준다.** GitHub 도 아주 큰 저장소에서는 `truncated`
    를 켜서 준다. 그걸 무시하면 "넷리스트가 없습니다" 라고 말하게 되는데,
    사실은 못 본 것이다 (헌법 2-2).
    """
    url = f"https://api.github.com/repos/{full_name}/git/trees/{urllib.parse.quote(branch)}?recursive=1"
    try:
        payload = _get_json(url, token)
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise GithubError("REPO_UNREADABLE", "저장소를 읽지 못했습니다. 권한과 브랜치를 확인해 주세요.") from exc

    entries = payload.get("tree") or []
    paths = [str(e["path"]) for e in entries if isinstance(e, dict) and e.get("type") == "blob"]
    truncated = bool(payload.get("truncated")) or len(paths) > MAX_TREE_FILES
    return paths[:MAX_TREE_FILES], truncated


#: 워크플로를 넣을 브랜치 이름.
#:
#: **기본 브랜치에 직접 안 쓴다.** 남의 저장소에 우리가 곧바로 커밋하면,
#: 그 파일이 마음에 안 들어도 이미 들어간 뒤다. PR 로 올리면 사람이 보고
#: 닫으면 그만이다 — **되돌릴 수 있는 형태로 준다.**
SETUP_BRANCH = "prefab/ci-설정"


def _put_json(url: str, token: str, data: dict, timeout: int = 20) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="PUT")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "prefab")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read())


def _post_gh(url: str, token: str, data: dict, timeout: int = 20) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "prefab")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read())


def open_setup_pr(token: str, full_name: str, branch: str, path: str, content: str) -> str:
    """워크플로 파일을 넣는 PR 을 연다. 돌려주는 값은 PR 주소.

    **이미 브랜치가 있으면 그 위에 덮어쓴다.** 두 번 눌렀다고 브랜치가 둘로
    늘어나면 사용자가 어느 쪽을 봐야 할지 모른다.
    """
    import base64

    api = f"https://api.github.com/repos/{full_name}"
    try:
        head = _get_json(f"{api}/git/ref/heads/{urllib.parse.quote(branch)}", token)
        base_sha = head["object"]["sha"]

        # 브랜치 만들기. 이미 있으면 422 가 나는데, 그건 정상 경로다.
        try:
            _post_gh(f"{api}/git/refs", token,
                     {"ref": f"refs/heads/{SETUP_BRANCH}", "sha": base_sha})
        except urllib.error.HTTPError as exc:
            if exc.code != 422:
                raise

        # 같은 파일이 이미 있으면 `sha` 를 줘야 덮어쓸 수 있다.
        existing = None
        try:
            got = _get_json(
                f"{api}/contents/{urllib.parse.quote(path)}?ref={urllib.parse.quote(SETUP_BRANCH)}",
                token,
            )
            existing = got.get("sha") if isinstance(got, dict) else None
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise

        payload = {
            "message": "Prefab — PR 마다 회로도와 코드를 대조한다",
            "content": base64.b64encode(content.encode()).decode(),
            "branch": SETUP_BRANCH,
        }
        if existing:
            payload["sha"] = existing
        _put_json(f"{api}/contents/{urllib.parse.quote(path)}", token, payload)

        try:
            made = _post_gh(f"{api}/pulls", token, {
                "title": "Prefab — PR 마다 회로도와 코드를 대조합니다",
                "head": SETUP_BRANCH,
                "base": branch,
                "body": _PR_BODY.format(path=path),
            })
            return str(made.get("html_url") or "")
        except urllib.error.HTTPError as exc:
            # 이미 열려 있는 PR 이 있으면 422. 그걸 찾아서 돌려준다.
            if exc.code != 422:
                raise
            owner = full_name.split("/")[0]
            open_prs = _get_json(f"{api}/pulls?head={owner}:{urllib.parse.quote(SETUP_BRANCH)}", token)
            if isinstance(open_prs, list) and open_prs:
                return str(open_prs[0].get("html_url") or "")
            raise

    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        if exc.code == 403:
            raise GithubError(
                "NO_PERMISSION",
                "이 저장소에 쓸 권한이 없습니다. 저장소 관리자에게 요청하거나 다른 저장소를 골라 주세요.",
            ) from None
        raise GithubError("PR_FAILED", f"PR 을 만들지 못했습니다 — {detail}") from None
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as exc:
        raise GithubError("GITHUB_UNREACHABLE", "GitHub 에 닿지 못했습니다. 잠시 후 다시 시도해 주세요.") from exc


_PR_BODY = """이 PR 은 [Prefab](https://prefab-web.onrender.com) 이 만들었습니다.

`{path}` 하나가 추가됩니다. 머지하면 **PR 마다 회로도와 펌웨어를 대조**해서,
코드가 쓰는 핀이 회로도에서 떨어졌거나 회로도가 바뀌었는데 코드가 안 따라온
자리를 보드 발주 전에 잡습니다.

## 머지 전에 하나 하셔야 합니다

저장소에 **`PREFAB_API_KEY`** 시크릿을 넣어 주세요. 키는 Prefab 의 「내 검사」
화면에서 만듭니다.

```
Settings → Secrets and variables → Actions → New repository secret
```

**저희가 대신 넣지 않습니다.** 시크릿을 쓰는 권한까지 받으면, 이 앱이 저장소의
모든 비밀값을 바꿀 수 있게 됩니다. 그 권한은 안 받는 편이 맞다고 봤습니다.

## 경로가 틀렸다면

파일 안의 `netlist` · `firmware` · `bom` 을 고치시면 됩니다. 저희가 저장소를
훑어 추측한 값이라 틀릴 수 있습니다.
"""
