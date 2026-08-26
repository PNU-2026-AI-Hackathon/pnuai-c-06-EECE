# GitHub 으로 로그인 — 켜는 순서

코드는 다 들어가 있다. **환경변수 넷을 채우면 켜지고, 비우면 꺼진다.**
꺼져 있는 동안 화면은 버튼을 아예 안 그린다 — 눌러도 안 되는 버튼을 두지 않는다.

> 이 문서의 절차 중 **1번은 사람이 해야 한다.** GitHub 계정 안에서 앱을 만들고
> 시크릿을 받는 일이라 자동화할 수 없다.

---

## 1. GitHub 에 OAuth 앱 만들기

<https://github.com/settings/developers> → **OAuth Apps** → **New OAuth App**

| 칸 | 넣을 값 |
|---|---|
| Application name | `Prefab` |
| Homepage URL | `https://prefab-web.onrender.com` |
| Authorization callback URL | `https://pnuai-c-06-eece-prefab.onrender.com/api/v1/auth/github/callback` |

**콜백 주소는 API 주소다. 화면 주소가 아니다.** 세션 쿠키를 API 도메인에
심어야 하기 때문이다. 여기를 화면 주소로 넣으면 로그인은 되는 것처럼 보이는데
쿠키가 엉뚱한 도메인에 붙어서 다음 요청부터 로그아웃 상태가 된다.

만들면 **Client ID** 가 보인다. **Generate a new client secret** 을 눌러
시크릿을 받는다 — **그 화면을 벗어나면 다시 못 본다.**

## 2. Render 에 환경변수 넣기

API 서비스(`pnuai-c-06-eece-prefab`) → **Environment** →

```
GITHUB_CLIENT_ID       (1번의 Client ID)
GITHUB_CLIENT_SECRET   (1번의 secret)
GITHUB_REDIRECT_URI    https://pnuai-c-06-eece-prefab.onrender.com/api/v1/auth/github/callback
WEB_APP_URL            https://prefab-web.onrender.com
```

`GITHUB_REDIRECT_URI` 는 **1번에 적은 것과 글자 하나까지 같아야 한다.**
다르면 GitHub 이 `redirect_uri_mismatch` 로 거절한다.

## 3. 켜졌는지 확인

```bash
curl -s https://pnuai-c-06-eece-prefab.onrender.com/api/v1/auth/me | grep -o '"github":{[^}]*}'
```

`{"enabled":true}` 가 나오면 화면에 버튼이 뜬다.

---

## 로컬에서 시험하려면

앱을 **하나 더** 만든다 (콜백이 다르므로 같은 앱을 못 쓴다).
콜백은 `http://localhost:8000/api/v1/auth/github/callback`.

```bash
export GITHUB_CLIENT_ID=...
export GITHUB_CLIENT_SECRET=...
export GITHUB_REDIRECT_URI=http://localhost:8000/api/v1/auth/github/callback
export WEB_APP_URL=http://localhost:5173
export COOKIE_SECURE=0
python -m uvicorn web.app:app --port 8000
```

---

## 알아 둘 것 두 가지

**① 저장소 권한은 안 받는다.** 요청하는 것은 `read:user user:email` 뿐이다.
로그인하려고 눌렀는데 "모든 저장소를 읽습니다" 가 뜨면 거기서 그만두기 때문이다.
나중에 저장소 연동을 붙이면 **그때 따로 물어본다.**

**② 시크릿이 state 서명 열쇠를 겸한다.** 시크릿을 바꾸면 그 순간 GitHub 으로
들어오던 사람들이 한 번 실패하고, 다시 누르면 된다. 흐름이 10분짜리라 그 이상은 아니다.
