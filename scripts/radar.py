#!/usr/bin/env python3
"""
radar.py — builds assets/radar-dark.svg and assets/radar-light.svg

This is a *self-declared* skills radar (Frontend / Backend / Security /
Databases / Cloud / Tools -> a 1-5 comfort level you set yourself in
assets/skills.json). It is intentionally not presented as a GitHub metric —
GitHub has no API for "skill level" and this script never pretends
otherwise. Edit assets/skills.json to update the shape.

Usage:
    python3 scripts/radar.py --config assets/skills.json --out assets
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from style import THEMES, esc, card_shell, wrap_svg  # noqa: E402

W, H = 380, 380


def render(theme_name, categories):
    t = THEMES[theme_name]
    body = card_shell(W, H, theme_name, "kiran-devhub — SKILLS.RADAR")
    cx, cy, R = W / 2, H / 2 + 12, 130
    n = len(categories)
    max_level = 5

    for frac in (0.2, 0.4, 0.6, 0.8, 1.0):
        pts = []
        for i in range(n):
            ang = -math.pi / 2 + i * 2 * math.pi / n
            pts.append((cx + R * frac * math.cos(ang), cy + R * frac * math.sin(ang)))
        body += (
            f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
            f'fill="none" stroke="{t["border"]}" stroke-width="1"/>'
        )

    for i, cat in enumerate(categories):
        ang = -math.pi / 2 + i * 2 * math.pi / n
        x2, y2 = cx + R * math.cos(ang), cy + R * math.sin(ang)
        body += f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{t["border"]}" stroke-width="1"/>'
        lx, ly = cx + (R + 26) * math.cos(ang), cy + (R + 16) * math.sin(ang)
        anchor = "middle"
        if math.cos(ang) > 0.3:
            anchor = "start"
        elif math.cos(ang) < -0.3:
            anchor = "end"
        body += (
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="10.5" '
            f'fill="{t["text"]}">{esc(cat["name"])}</text>'
        )

    poly = []
    for i, cat in enumerate(categories):
        ang = -math.pi / 2 + i * 2 * math.pi / n
        r = R * (cat["level"] / max_level) * 0.92
        poly.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    body += (
        f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in poly)}" '
        f'fill="{t["accent2"]}" fill-opacity="0.22" stroke="{t["accent2"]}" stroke-width="2"/>'
    )
    for x, y in poly:
        body += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{t["accent2"]}"/>'

    body += (
        f'<text x="{W-16}" y="{H-10}" text-anchor="end" '
        f'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="9" '
        f'fill="{t["muted"]}">source: assets/skills.json</text>'
    )
    return wrap_svg(W, H, theme_name, body, "kiran-devhub skills radar")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="assets/skills.json")
    ap.add_argument("--out", default="assets")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)
    categories = cfg["radar"]

    os.makedirs(args.out, exist_ok=True)
    for theme_name in ("dark", "light"):
        svg = render(theme_name, categories)
        path = os.path.join(args.out, f"radar-{theme_name}.svg")
        with open(path, "w") as f:
            f.write(svg)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
