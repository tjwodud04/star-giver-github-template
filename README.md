# Star Giver GitHub

Auto follow-back & star profile README repos (`username/username`) for your GitHub followers.
Runs daily via GitHub Actions — no server needed.

GitHub 팔로워 자동 맞팔 & 프로필 README 레포 자동 스타.
GitHub Actions로 매일 자동 실행 — 서버 불필요.

---

## Table of Contents

- [Features / 기능](#features--기능)
- [Quick Start / 빠른 시작](#quick-start--빠른-시작)
- [How It Works / 동작 방식](#how-it-works--동작-방식)
- [Configuration / 설정](#configuration--설정)
- [License](#license)

---

## Features / 기능

| Feature | 기능 |
|---|---|
| Daily auto-run via GitHub Actions | GitHub Actions 매일 자동 실행 |
| Skip if no follower changes | 팔로워 변동 없으면 스킵 |
| Auto follow-back | 자동 맞팔 |
| Auto star `username/username` repo | 프로필 README 레포 자동 스타 |
| No server required | 서버 불필요 (GitHub Actions) |

---

## Quick Start / 빠른 시작

### 1. Fork or Use Template / 포크 또는 템플릿 사용

Click **"Use this template"** or **"Fork"** at the top of this page.

이 페이지 상단의 **"Use this template"** 또는 **"Fork"** 클릭.

### 2. Create Personal Access Token / 토큰 생성

Go to [**GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)**](https://github.com/settings/tokens/new)

| Scope | Required |
|---|---|
| `user:follow` | Yes |
| `public_repo` | Yes |

### 3. Set Secrets & Variables / 시크릿 & 변수 설정

Go to your forked repo: **Settings > Secrets and variables > Actions**

| Type | Name | Value |
|---|---|---|
| **Secret** | `GH_PAT` | Your Personal Access Token |
| **Variable** | `TARGET_USERNAME` | Your GitHub username |

### 4. Run / 실행

| Method | How / 방법 |
|---|---|
| Auto | Runs daily at 00:00 UTC / 매일 UTC 00:00 자동 실행 |
| Manual | **Actions** tab > **Star Giver** > **Run workflow** |

---

## How It Works / 동작 방식

```
Fetch followers & following
        │
Compare with previous state (state.json)
        │
   ┌────┴────┐
   │ Changed? │
   └────┬────┘
   No   │   Yes
   │    │    │
 Skip   │    ├─ Follow back new followers
        │    ├─ Star their profile README repos
        │    └─ Save updated state
        │
       Done
```

---

## Configuration / 설정

Edit the cron schedule in [`.github/workflows/star-giver.yml`](.github/workflows/star-giver.yml):

워크플로우 파일에서 cron 스케줄 수정:

```yaml
schedule:
  - cron: '0 0 * * *'  # UTC — adjust to your timezone
```

| Timezone | Cron | Example |
|---|---|---|
| UTC | `0 0 * * *` | 00:00 UTC |
| KST (UTC+9) | `0 0 * * *` | 09:00 KST |
| EST (UTC-5) | `0 5 * * *` | 00:00 EST |
| PST (UTC-8) | `0 8 * * *` | 00:00 PST |

---

## License

[MIT](LICENSE)
