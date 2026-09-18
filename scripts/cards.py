#!/usr/bin/env python3
"""
cards.py — builds assets/card-stats-dark.svg and assets/card-stats-light.svg

Pulls real numbers from the GitHub REST API for the configured username:
  - public repos, followers, following
  - total stars and forks across owned, non-fork repos
  - account age (years on GitHub)

No numbers are ever invented. If the API can't be reached (no token, rate
limited, offline), a clearly-labeled placeholder card is written instead —
see scripts/style.placeholder_note — and the script exits 0 so it never
breaks a CI run; .github/workflows/profile.yml re-runs it on a schedule
with an authenticated token so the real card takes over automatically.

Usage:
    python3 scripts/cards.py --username kiran-devhub --out assets
Env:
    GITHUB_TOKEN   optional, raises the API rate limit substantially
"""
from __future__ import annotations
import argparse
import os
import sys
import urllib.request
import urllib.error
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from style import THEMES, esc, card_shell, placeholder_note, wrap_svg  # noqa: E402

API = "https://api.github.com"
W, H = 460, 220


def _get(url, token=None):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def fetch_stats(username, token=None):
    user = _get(f"{API}/users/{username}", token)
    repos = []
    page = 1
    while True:
        batch = _get(f"{API}/users/{username}/repos?per_page=100&page={page}&type=owner", token)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    owned_nonfork = [r for r in repos if not r.get("fork")]
    total_stars = sum(r.get("stargazers_count", 0) for r in owned_nonfork)
    total_forks = sum(r.get("forks_count", 0) for r in owned_nonfork)
    created = datetime.strptime(user["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    years = (datetime.now(timezone.utc) - created).days / 365.25

    return dict(
        public_repos=user.get("public_repos", len(owned_nonfork)),
        followers=user.get("followers", 0),
        following=user.get("following", 0),
        total_stars=total_stars,
        total_forks=total_forks,
        years_on_github=round(years, 1),
        fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


def render_card(theme_name, username, stats):
    t = THEMES[theme_name]
    body = card_shell(W, H, theme_name, f"{username} — GITHUB.STATS")
    if stats is None:
        body += placeholder_note(W, H, theme_name, "live stats unavailable at build time")
        return wrap_svg(W, H, theme_name, body, f"{username} GitHub stats (pending)")

    rows = [
        ("PUBLIC REPOS", stats["public_repos"]),
        ("FOLLOWERS", stats["followers"]),
        ("FOLLOWING", stats["following"]),
        ("TOTAL STARS", stats["total_stars"]),
        ("TOTAL FORKS", stats["total_forks"]),
        ("YEARS ON GITHUB", stats["years_on_github"]),
    ]
    y = 62
    col_w = W / 2
    for i, (label, val) in enumerate(rows):
        cx = 24 + (i % 2) * col_w
        cy = y + (i // 2) * 48
        body += (
            f'<text x="{cx}" y="{cy}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
            f'font-size="20" font-weight="700" fill="{t["accent"]}">{esc(val)}</text>'
            f'<text x="{cx}" y="{cy+17}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
            f'font-size="9.5" letter-spacing="1.4" fill="{t["muted"]}">{esc(label)}</text>'
        )
    body += (
        f'<text x="{W-16}" y="{H-12}" text-anchor="end" '
        f'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="9" '
        f'fill="{t["muted"]}">updated {esc(stats["fetched_at"])}</text>'
    )
    return wrap_svg(W, H, theme_name, body, f"{username} GitHub stats")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", default=os.environ.get("GITHUB_PROFILE_USER", "kiran-devhub"))
    ap.add_argument("--out", default="assets")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    stats = None
    try:
        stats = fetch_stats(args.username, token)
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, TimeoutError) as e:
        print(f"[cards.py] live fetch failed, writing placeholder card: {e}", file=sys.stderr)

    os.makedirs(args.out, exist_ok=True)
    for theme_name in ("dark", "light"):
        svg = render_card(theme_name, args.username, stats)
        path = os.path.join(args.out, f"card-stats-{theme_name}.svg")
        with open(path, "w") as f:
            f.write(svg)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
