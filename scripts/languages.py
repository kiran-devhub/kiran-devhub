#!/usr/bin/env python3
"""
languages.py — builds:
    assets/metrics.languages.svg     (horizontal bar breakdown, theme-neutral)
    assets/radar-langs-dark.svg
    assets/radar-langs-light.svg

Pulls real per-repo language byte counts from the GitHub REST API
(/repos/{owner}/{repo}/languages) and aggregates them across all owned,
non-fork repos. Nothing here is invented: if the API is unreachable the
scripts write a labeled placeholder instead of guessing at percentages.
Also writes assets/langmix.json as a small cache of the last successful
fetch, so the numbers are inspectable/configurable.

Usage:
    python3 scripts/languages.py --username kiran-devhub --out assets
Env:
    GITHUB_TOKEN   optional, raises the API rate limit substantially
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from style import THEMES, esc, card_shell, placeholder_note, wrap_svg  # noqa: E402

API = "https://api.github.com"
BAR_W, BAR_H = 460, 220
RADAR_W, RADAR_H = 380, 380
TOP_N = 6

LANG_COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Python": "#3572A5",
    "Java": "#b07219", "C": "#555555", "C++": "#f34b7d", "HTML": "#e34c26",
    "CSS": "#563d7c", "Shell": "#89e051", "Go": "#00ADD8", "Rust": "#dea584",
}


def _get(url, token=None):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def fetch_language_mix(username, token=None, max_repos=60):
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
    repos = [r for r in repos if not r.get("fork")][:max_repos]

    totals = Counter()
    for r in repos:
        try:
            langs = _get(r["languages_url"], token)
        except (urllib.error.URLError, urllib.error.HTTPError):
            continue
        for lang, byte_count in langs.items():
            totals[lang] += byte_count

    grand_total = sum(totals.values()) or 1
    mix = {lang: round(count / grand_total * 100, 2) for lang, count in totals.items()}
    return dict(mix=mix, fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))


def render_bars(theme_name, username, data):
    t = THEMES[theme_name]
    body = card_shell(BAR_W, BAR_H, theme_name, f"{username} — TOP.LANGUAGES")
    if data is None:
        body += placeholder_note(BAR_W, BAR_H, theme_name, "language mix unavailable at build time")
        return wrap_svg(BAR_W, BAR_H, theme_name, body, f"{username} top languages (pending)")

    top = sorted(data["mix"].items(), key=lambda kv: -kv[1])[:TOP_N]
    y = 54
    track_w = BAR_W - 140
    for lang, pct in top:
        color = LANG_COLORS.get(lang, t["accent"])
        body += (
            f'<text x="20" y="{y+11}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
            f'font-size="11.5" fill="{t["text"]}">{esc(lang)}</text>'
            f'<rect x="118" y="{y}" width="{track_w}" height="10" rx="5" fill="{t["track"]}"/>'
            f'<rect x="118" y="{y}" width="{max(4, track_w*pct/100):.1f}" height="10" rx="5" fill="{color}"/>'
            f'<text x="{BAR_W-18}" y="{y+9}" text-anchor="end" '
            f'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="10.5" '
            f'fill="{t["muted"]}">{pct:.1f}%</text>'
        )
        y += 26
    body += (
        f'<text x="{BAR_W-16}" y="{BAR_H-10}" text-anchor="end" '
        f'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="9" '
        f'fill="{t["muted"]}">updated {esc(data["fetched_at"])}</text>'
    )
    return wrap_svg(BAR_W, BAR_H, theme_name, body, f"{username} top languages")


def render_radar(theme_name, username, data):
    t = THEMES[theme_name]
    body = card_shell(RADAR_W, RADAR_H, theme_name, f"{username} — LANGUAGE.RADAR")
    cx, cy, R = RADAR_W / 2, RADAR_H / 2 + 12, 130

    if data is None:
        body += placeholder_note(RADAR_W, RADAR_H, theme_name, "language mix unavailable at build time")
        return wrap_svg(RADAR_W, RADAR_H, theme_name, body, f"{username} language radar (pending)")

    top = sorted(data["mix"].items(), key=lambda kv: -kv[1])[:TOP_N]
    n = max(3, len(top))
    max_val = max((v for _, v in top), default=1) or 1

    # grid rings
    for frac in (0.25, 0.5, 0.75, 1.0):
        pts = []
        for i in range(n):
            ang = -math.pi / 2 + i * 2 * math.pi / n
            pts.append((cx + R * frac * math.cos(ang), cy + R * frac * math.sin(ang)))
        body += (
            f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
            f'fill="none" stroke="{t["border"]}" stroke-width="1"/>'
        )
    # axes + labels
    for i, (lang, val) in enumerate(top):
        ang = -math.pi / 2 + i * 2 * math.pi / n
        x2, y2 = cx + R * math.cos(ang), cy + R * math.sin(ang)
        body += f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{t["border"]}" stroke-width="1"/>'
        lx, ly = cx + (R + 22) * math.cos(ang), cy + (R + 16) * math.sin(ang)
        anchor = "middle"
        if math.cos(ang) > 0.3:
            anchor = "start"
        elif math.cos(ang) < -0.3:
            anchor = "end"
        body += (
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="10.5" '
            f'fill="{t["text"]}">{esc(lang)}</text>'
        )
    # data polygon
    poly = []
    for i, (lang, val) in enumerate(top):
        ang = -math.pi / 2 + i * 2 * math.pi / n
        r = R * (val / max_val) * 0.92
        poly.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    body += (
        f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in poly)}" '
        f'fill="{t["accent"]}" fill-opacity="0.25" stroke="{t["accent"]}" stroke-width="2"/>'
    )
    for x, y in poly:
        body += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{t["accent"]}"/>'

    return wrap_svg(RADAR_W, RADAR_H, theme_name, body, f"{username} language radar")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", default=os.environ.get("GITHUB_PROFILE_USER", "kiran-devhub"))
    ap.add_argument("--out", default="assets")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    data = None
    try:
        data = fetch_language_mix(args.username, token)
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, TimeoutError) as e:
        print(f"[languages.py] live fetch failed, writing placeholder cards: {e}", file=sys.stderr)

    os.makedirs(args.out, exist_ok=True)
    if data is not None:
        with open(os.path.join(args.out, "langmix.json"), "w") as f:
            json.dump(data, f, indent=2)

    for theme_name in ("dark", "light"):
        bars = render_bars(theme_name, args.username, data)
        path = os.path.join(args.out, "metrics.languages.svg") if theme_name == "dark" else None
        # metrics.languages.svg is theme-neutral per the file spec; write the dark
        # rendering once, and still produce themed radar-langs-*.svg below.
        if path:
            with open(path, "w") as f:
                f.write(bars)
            print(f"wrote {path}")

        radar = render_radar(theme_name, args.username, data)
        rpath = os.path.join(args.out, f"radar-langs-{theme_name}.svg")
        with open(rpath, "w") as f:
            f.write(radar)
        print(f"wrote {rpath}")


if __name__ == "__main__":
    main()
