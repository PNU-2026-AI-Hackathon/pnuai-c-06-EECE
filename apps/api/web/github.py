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
SAFE_NEXT = ("/mine", "/check", "/pricing", "/")


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
