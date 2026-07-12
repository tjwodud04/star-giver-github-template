# Star Giver GitHub

Auto follow-back & star the profile-README repo (`username/username`) of your GitHub followers.
Runs daily via GitHub Actions — no server needed.

GitHub 팔로워 자동 맞팔 & 프로필 README 레포(`username/username`) 자동 스타.
GitHub Actions로 매일 자동 실행 — 서버 불필요.

---

## Table of Contents

- [Features / 기능](#features--기능)
- [Quick Start / 빠른 시작](#quick-start--빠른-시작)
- [How It Works / 동작 방식](#how-it-works--동작-방식)
- [Project Structure / 프로젝트 구조](#project-structure--프로젝트-구조)
- [Configuration / 설정](#configuration--설정)
- [Local Development / 로컬 개발](#local-development--로컬-개발)
- [License](#license)

---

## Features / 기능

| Feature | 기능 |
|---|---|
| Daily auto-run via GitHub Actions | GitHub Actions 매일 자동 실행 |
| Skip when followers haven't changed | 팔로워 변동 없으면 스킵 |
| Auto follow-back | 자동 맞팔 |
| Auto star `username/username` repo | 프로필 README 레포 자동 스타 |
| Graceful rate-limit & retry handling | 레이트리밋/재시도 자동 처리 |
| No server required | 서버 불필요 (GitHub Actions) |

---

## Quick Start / 빠른 시작

### 1. Use this template / 템플릿 사용

Click **"Use this template" → "Create a new repository"** at the top of this page
(or **Fork** it).

이 페이지 상단의 **"Use this template" → "Create a new repository"** 클릭 (또는 **Fork**).

### 2. Create a fine-grained token / 파인그레인드 토큰 생성

Create a **fine-grained** personal access token (recommended over classic tokens):
[**Settings → Developer settings → Fine-grained tokens → Generate new token**](https://github.com/settings/personal-access-tokens/new).

파인그레인드 개인 액세스 토큰 생성 (클래식 토큰보다 권장):

| Setting | Value / 값 |
|---|---|
| **Resource owner** | Your own account / 본인 계정 |
| **Expiration** | Keep it short (e.g. 90 days) / 짧게 (예: 90일) |
| **Repository access** | **Public repositories (read-only)** — that's enough |
| **Account permissions → Followers** | **Read and write** |
| **Account permissions → Starring** | **Read and write** |

Those are the **only** permissions this bot needs (least privilege).
It does **not** need repository write access — the workflow commits `state.json`
with the built-in `GITHUB_TOKEN`, not with your `GH_PAT`.

이 봇에 필요한 권한은 위 두 가지(`Followers`, `Starring` 쓰기)뿐입니다 (최소 권한).
레포지토리 쓰기 권한은 필요 없습니다 — `state.json` 커밋은 `GH_PAT`가 아니라
워크플로우 내장 `GITHUB_TOKEN`이 담당합니다.

> Prefer a classic token? Then grant the `user:follow` and `public_repo` scopes.
> Fine-grained is recommended because you can scope it down and set an expiry.

### 3. Set the secret & variable / 시크릿 & 변수 설정

In your new repo: **Settings → Secrets and variables → Actions**

| Type | Name | Value |
|---|---|---|
| **Secret** | `GH_PAT` | Your fine-grained token |
| **Variable** | `TARGET_USERNAME` | Your GitHub username |

### 4. Enable & run Actions / 액션 활성화 및 실행

Open the **Actions** tab and enable workflows (templated repos start disabled).

**Actions** 탭에서 워크플로우를 활성화하세요 (템플릿 레포는 기본 비활성).

| Method | How / 방법 |
|---|---|
| Auto | Runs daily at 00:00 UTC / 매일 UTC 00:00 자동 실행 |
| Manual | **Actions** tab → **Star Giver** → **Run workflow** |

---

## How It Works / 동작 방식

```
Fetch followers & following
        │
Compare with previous snapshot (state.json)
        │
   ┌────┴─────┐
   │ Changed? │
   └────┬─────┘
   No   │   Yes
   │    │    │
 Skip   │    ├─ Follow back followers you don't follow yet
        │    ├─ Star their profile-README repo (user/user)
        │    └─ Save the updated snapshot
        │
       Done
```

On the **first run** (no snapshot yet) it stars every current follower's profile
repo; afterwards it only acts on **newly added** followers.

첫 실행(스냅샷 없음)에는 모든 팔로워의 프로필 레포에 스타를 주고,
이후에는 **새로 늘어난** 팔로워만 처리합니다.

---

## Project Structure / 프로젝트 구조

```
stargiver/
├── __main__.py       # `python -m stargiver` entry point
├── app.py            # orchestration (fetch → compare → follow → star → save)
├── config.py         # constants + env-driven Config
├── github_client.py  # typed httpx GitHub REST client (pagination, retries, rate limits)
├── followers.py      # follow-back logic
├── stars.py          # star-profile-repo logic
├── state.py          # load/save state.json snapshot
└── errors.py         # typed exceptions
```

---

## Configuration / 설정

**Schedule.** Edit the cron in [`.github/workflows/star-giver.yml`](.github/workflows/star-giver.yml):

```yaml
schedule:
  - cron: '0 0 * * *'  # UTC — adjust to your timezone
```

| Timezone | Cron | Runs at |
|---|---|---|
| UTC | `0 0 * * *` | 00:00 UTC |
| KST (UTC+9) | `0 0 * * *` | 09:00 KST |
| EST (UTC-5) | `0 5 * * *` | 00:00 EST |
| PST (UTC-8) | `0 8 * * *` | 00:00 PST |

**Behaviour.** Everything tunable lives in `stargiver/config.py` and can be
overridden with environment variables (see [`.env.example`](.env.example)):
`STARGIVER_FOLLOW_DELAY`, `STARGIVER_STAR_DELAY`, `STARGIVER_REQUEST_TIMEOUT`,
`STARGIVER_MAX_RETRIES`.

---

## Local Development / 로컬 개발

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # then edit GH_PAT and TARGET_USERNAME
set -a; source .env; set +a # export the vars (bash/zsh)

python -m stargiver
```

`state.json` is written next to the package and is committed automatically by
CI. Running locally will follow/star for real, so use a throwaway token if you
just want to experiment.

---

## License

[MIT](LICENSE) © tjwodud04
