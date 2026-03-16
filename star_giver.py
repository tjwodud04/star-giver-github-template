import json
import os
import sys
import time

import requests

GITHUB_TOKEN = os.environ.get("GH_PAT")
GITHUB_USERNAME = os.environ.get("TARGET_USERNAME")
API_BASE = "https://api.github.com"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")


def get_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_all_pages(url):
    results = []
    page = 1
    while True:
        resp = requests.get(
            url, headers=get_headers(), params={"per_page": 100, "page": page}
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        results.extend(data)
        page += 1
    return results


def get_followers():
    url = f"{API_BASE}/users/{GITHUB_USERNAME}/followers"
    return {u["login"] for u in get_all_pages(url)}


def get_following():
    url = f"{API_BASE}/users/{GITHUB_USERNAME}/following"
    return {u["login"] for u in get_all_pages(url)}


def follow_user(username):
    url = f"{API_BASE}/user/following/{username}"
    resp = requests.put(url, headers=get_headers())
    if resp.status_code == 204:
        print(f"  [Follow] {username} - done")
        return True
    print(f"  [Follow] {username} - failed (HTTP {resp.status_code})")
    return False


def star_repo(owner, repo):
    url = f"{API_BASE}/user/starred/{owner}/{repo}"
    check = requests.get(url, headers=get_headers())
    if check.status_code == 204:
        print(f"  [Star] {owner}/{repo} - already starred")
        return False
    resp = requests.put(url, headers=get_headers())
    if resp.status_code == 204:
        print(f"  [Star] {owner}/{repo} - done")
        return True
    print(f"  [Star] {owner}/{repo} - failed (HTTP {resp.status_code})")
    return False


def check_repo_exists(owner, repo):
    url = f"{API_BASE}/repos/{owner}/{repo}"
    return requests.get(url, headers=get_headers()).status_code == 200


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"followers": [], "following": []}


def save_state(followers, following):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"followers": sorted(followers), "following": sorted(following)},
            f,
            indent=2,
            ensure_ascii=False,
        )


def main():
    if not GITHUB_TOKEN or not GITHUB_USERNAME:
        print("Error: GH_PAT and TARGET_USERNAME environment variables are required.")
        sys.exit(1)

    print(f"=== Star Giver GitHub ({GITHUB_USERNAME}) ===\n")

    print("[1/4] Fetching followers...")
    current_followers = get_followers()
    print(f"  Followers: {len(current_followers)}")

    print("[2/4] Fetching following...")
    current_following = get_following()
    print(f"  Following: {len(current_following)}")

    # Compare with previous state
    prev_state = load_state()
    prev_followers = set(prev_state["followers"])

    new_followers = current_followers - prev_followers
    lost_followers = prev_followers - current_followers

    if new_followers:
        print(f"\n  New followers (+{len(new_followers)}): {', '.join(sorted(new_followers))}")
    if lost_followers:
        print(f"  Unfollowed (-{len(lost_followers)}): {', '.join(sorted(lost_followers))}")

    if current_followers == prev_followers and prev_state["followers"]:
        print("\nNo follower changes - skipping.")
        save_state(current_followers, current_following)
        print("\n=== Done (no changes) ===")
        return

    # Follow back
    not_following_back = current_followers - current_following
    print(f"\n[3/4] Follow back ({len(not_following_back)} users)...")

    follow_count = 0
    star_count = 0

    for user in sorted(not_following_back):
        print(f"\n>> {user}")
        if follow_user(user):
            follow_count += 1
        time.sleep(0.5)

    # Star profile README repos
    targets = new_followers if prev_state["followers"] else current_followers
    print(f"\n[4/4] Star profile READMEs ({len(targets)} users)...")

    for user in sorted(targets):
        if check_repo_exists(user, user):
            if star_repo(user, user):
                star_count += 1
        else:
            print(f"  [Star] {user}/{user} - no repo, skip")
        time.sleep(0.3)

    # Save state
    updated_following = current_following | not_following_back
    save_state(current_followers, updated_following)

    print(f"\n=== Done ===")
    print(f"  New follows: {follow_count}")
    print(f"  New stars: {star_count}")

    # GitHub Actions output
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"follow_count={follow_count}\n")
            f.write(f"star_count={star_count}\n")
            f.write(f"new_followers={len(new_followers)}\n")


if __name__ == "__main__":
    main()
