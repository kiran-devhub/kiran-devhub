#!/usr/bin/env python3
"""
generate.py — builds assets/banner-dark.svg and assets/banner-light.svg

Usage:
    python3 scripts/banner/generate.py

Reads:
    assets/source/kiran.png   (source portrait photo)
    assets/skills.json        (used only for the short "stack" chip preview)

Writes:
    assets/banner-dark.svg
    assets/banner-light.svg

Everything drawn (the portrait, the shield/code/lock morph targets, all
text) is generated here from real inputs — there are no invented GitHub
numbers in this file. Live stats/cards are produced separately by
scripts/cards.py / scripts/languages.py / scripts/radar.py, which run in
CI (see .github/workflows/profile.yml) so they always reflect real data.
"""
from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import halftone as H  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ASSETS = os.path.join(ROOT, "assets")
SRC_PHOTO = os.path.join(ASSETS, "source", "kiran.png")

W, H_TOTAL = 980, 480
WORK_W, WORK_H = 260, 312

# Crop box in the *original* source photo's pixel coordinates.
# Chosen to center head + upper torso/hoodie without cropping the face.
CROP_BOX = (230, 60, 930, 900)

THEMES = {
    "dark": dict(
        bg="#05080c",
        panel="#0b141a",
        panel2="#0d1720",
        border="#173039",
        border_bright="#2dd8c8",
        grid="#0e2129",
        text="#dff7f1",
        muted="#5f8a86",
        accent="#38f2d8",
        accent2="#ff3e7f",
        accent3="#ffcf5c",
        scan="#38f2d833",
        shadow_ok=True,
    ),
    "light": dict(
        bg="#eef3f4",
        panel="#ffffff",
        panel2="#f5f9f9",
        border="#c7dbdc",
        border_bright="#0f8b7d",
        grid="#dbe9ea",
        text="#0b1c1c",
        muted="#4d6567",
        accent="#0f8b7d",
        accent2="#c81361",
        accent3="#a56a00",
        scan="#0f8b7d1f",
        shadow_ok=False,
    ),
}


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def dots_group(dots, gid, ox, oy, scale, color, extra_attrs=""):
    parts = [f'<g id="{gid}" {extra_attrs}>']
    for (x, y, r, op) in dots:
        cx = round(ox + x * scale, 1)
        cy = round(oy + y * scale, 1)
        rr = round(r * scale, 2)
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="{color}" fill-opacity="{op}"/>')
    parts.append("</g>")
    return "".join(parts)


def build_morph_panel(panel_x, panel_y, panel_w, panel_h, dot_sets, theme, cycle=12):
    """dot_sets: dict of name -> (dots, w, h). Renders 4 stacked groups
    (portrait, shield, code, lock) cross-fading in sequence, looping."""
    scale = min(panel_w / WORK_W, panel_h / WORK_H)
    draw_w, draw_h = WORK_W * scale, WORK_H * scale
    ox = panel_x + (panel_w - draw_w) / 2
    oy = panel_y + (panel_h - draw_h) / 2

    order = ["portrait", "shield", "code", "lock"]
    n = len(order)
    seg = cycle / n
    # each state: fade in over 0.6s, hold, fade out over 0.6s, dark otherwise
    groups = []
    for i, name in enumerate(order):
        dots, w, h = dot_sets[name]
        color = theme["accent"] if name != "portrait" else theme["accent"]
        start = i * seg
        t0 = start / cycle
        t_in_end = (start + 0.6) / cycle
        t_out_start = (start + seg - 0.6) / cycle
        t_end = (start + seg) / cycle
        # keyTimes must be strictly increasing 0..1; clamp tiny segments
        keytimes = [0, t0, t_in_end, t_out_start, t_end, 1]
        keytimes = sorted(set(round(k, 4) for k in keytimes))
        # build opacity values aligned to keytimes: 0 elsewhere, 1 during hold
        vals = []
        for k in keytimes:
            if k <= t0 or k >= t_end:
                vals.append("0")
            elif abs(k - t_in_end) < 1e-6 or (t0 < k < t_out_start):
                vals.append("1")
            elif abs(k - t_out_start) < 1e-6:
                vals.append("1")
            else:
                vals.append("0")
        kt_str = ";".join(str(k) for k in keytimes)
        val_str = ";".join(vals)
        g = dots_group(dots, f"morph-{name}", ox, oy, scale, color)
        g = g.replace(
            "<g id=",
            "<g opacity=\"0\" id=",
            1,
        )
        anim = (f'<animate xlink:href="#morph-{name}" attributeName="opacity" '
                f'keyTimes="{kt_str}" values="{val_str}" dur="{cycle}s" '
                f'repeatCount="indefinite"/>')
        groups.append(g + anim)

    scan_line = (
        f'<line x1="{ox}" y1="{oy}" x2="{ox+draw_w}" y2="{oy}" '
        f'stroke="{theme["accent"]}" stroke-width="1.4" opacity="0.75">'
        f'<animate attributeName="y1" values="{oy};{oy+draw_h};{oy}" dur="{cycle/2}s" repeatCount="indefinite"/>'
        f'<animate attributeName="y2" values="{oy};{oy+draw_h};{oy}" dur="{cycle/2}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0.85;0.15;0.85" dur="2.4s" repeatCount="indefinite"/>'
        f'</line>'
    )

    frame = (
        f'<rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="10" '
        f'fill="{theme["panel2"]}" stroke="{theme["border"]}" stroke-width="1"/>'
    )
    clip_id = "morphClip"
    clip = (f'<clipPath id="{clip_id}"><rect x="{panel_x}" y="{panel_y}" '
            f'width="{panel_w}" height="{panel_h}" rx="10"/></clipPath>')

    labels = ["PORTRAIT", "SHIELD", "CODE", "LOCK"]
    label_x = panel_x + 10
    label_y = panel_y + panel_h - 12
    label_anim_parts = []
    for i, lab in enumerate(labels):
        start = i * seg
        t0 = round(start / cycle, 4)
        t1 = round((start + seg) / cycle, 4)
        kt = sorted(set([0, t0, min(t0 + 0.02, 1), max(t1 - 0.02, 0), t1, 1]))
        vals = []
        for k in kt:
            vals.append("1" if t0 <= k <= t1 else "0")
        label_anim_parts.append(
            f'<text x="{label_x}" y="{label_y}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
            f'font-size="9" letter-spacing="2" fill="{theme["muted"]}" opacity="0">{lab}'
            f'<animate attributeName="opacity" keyTimes="{";".join(map(str,kt))}" '
            f'values="{";".join(vals)}" dur="{cycle}s" repeatCount="indefinite"/></text>'
        )

    progress = (
        f'<rect x="{panel_x+10}" y="{panel_y+panel_h-6}" width="{panel_w-20}" height="2.4" rx="1.2" '
        f'fill="{theme["border"]}"/>'
        f'<rect x="{panel_x+10}" y="{panel_y+panel_h-6}" width="0" height="2.4" rx="1.2" fill="{theme["accent"]}">'
        f'<animate attributeName="width" values="0;{panel_w-20};0" dur="{cycle}s" repeatCount="indefinite"/>'
        f'</rect>'
    )

    return (
        f'<g clip-path="url(#{clip_id})">{clip}{frame}{"".join(groups)}{scan_line}</g>'
        + progress
        + "".join(label_anim_parts)
    )


def build_quick_link(x, y, w, h, label, href, theme, icon):
    rx = 8
    body = (
        f'<a xlink:href="{esc(href)}" target="_blank">'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
        f'fill="{theme["panel2"]}" stroke="{theme["border_bright"]}" stroke-width="1" opacity="0.9"/>'
        f'<text x="{x+16}" y="{y+h/2+4}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
        f'font-size="12" fill="{theme["text"]}">{icon}  {esc(label)}</text>'
        f'</a>'
    )
    return body


def build_svg(theme_name, dot_sets):
    t = THEMES[theme_name]
    defs = f'''
    <defs>
      <linearGradient id="bgGrad-{theme_name}" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="{t['bg']}"/>
        <stop offset="1" stop-color="{t['panel']}"/>
      </linearGradient>
      <pattern id="grid-{theme_name}" width="26" height="26" patternUnits="userSpaceOnUse">
        <path d="M26 0H0V26" fill="none" stroke="{t['grid']}" stroke-width="1"/>
      </pattern>
      <filter id="glow-{theme_name}" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="2.4" result="blur"/>
        <feMerge>
          <feMergeNode in="blur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
      <pattern id="scan-{theme_name}" width="4" height="7" patternUnits="userSpaceOnUse">
        <rect width="4" height="1.1" fill="{t['scan']}"/>
      </pattern>
    </defs>
    '''

    outer = (
        f'<rect x="1" y="1" width="{W-2}" height="{H_TOTAL-2}" rx="16" '
        f'fill="url(#bgGrad-{theme_name})" stroke="{t["border_bright"]}" stroke-width="1.4"/>'
        f'<rect x="1" y="1" width="{W-2}" height="{H_TOTAL-2}" rx="16" fill="url(#grid-{theme_name})" opacity="0.5"/>'
        f'<rect x="1" y="1" width="{W-2}" height="{H_TOTAL-2}" rx="16" fill="url(#scan-{theme_name})" opacity="0.5"/>'
    )

    # title bar
    titlebar = (
        f'<circle cx="26" cy="24" r="5.5" fill="#ff5f57"/>'
        f'<circle cx="44" cy="24" r="5.5" fill="#febc2e"/>'
        f'<circle cx="62" cy="24" r="5.5" fill="#28c840"/>'
        f'<text x="{W/2}" y="28" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
        f'font-size="12" fill="{t["muted"]}">kiran-devhub — cyberdeck.sh</text>'
        f'<line x1="0" y1="42" x2="{W}" y2="42" stroke="{t["border"]}" stroke-width="1"/>'
    )

    # left panel: VISUAL.MAP / MORPH.ANIMATION
    lp_x, lp_y, lp_w, lp_h = 24, 60, 300, 366
    left_label = (
        f'<text x="{lp_x}" y="{lp_y-10}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
        f'font-size="11" letter-spacing="2" fill="{t["accent"]}">VISUAL.MAP // MORPH.ANIMATION</text>'
    )
    morph = build_morph_panel(lp_x, lp_y, lp_w, lp_h - 24, dot_sets, t)

    # right panel: SYSTEM.INFO
    rp_x, rp_y, rp_w = 348, 60, W - 348 - 24
    right_label = (
        f'<text x="{rp_x}" y="{rp_y-10}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
        f'font-size="11" letter-spacing="2" fill="{t["accent"]}">SYSTEM.INFO</text>'
    )
    info_frame = (
        f'<rect x="{rp_x}" y="{rp_y}" width="{rp_w}" height="196" rx="10" '
        f'fill="{t["panel2"]}" stroke="{t["border"]}" stroke-width="1"/>'
    )
    info_lines = [
        ("NAME", "Kiran Kumar Behera"),
        ("ROLE", "Developer / Cybersecurity"),
        ("FOCUS", "Secure Web Applications"),
        ("LOCATION", "India"),
        ("STATUS", "Building + Learning + Shipping"),
    ]
    info_text = []
    ly = rp_y + 28
    cursor_row = len(info_lines) - 1
    for i, (k, v) in enumerate(info_lines):
        tail = ""
        if i == cursor_row:
            tail = (
                f'<tspan fill="{t["accent"]}"> &#9608;'
                f'<animate attributeName="opacity" values="1;1;0;0;1" '
                f'keyTimes="0;0.45;0.5;0.95;1" dur="1.1s" repeatCount="indefinite"/>'
                f'</tspan>'
            )
        info_text.append(
            f'<text x="{rp_x+18}" y="{ly}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
            f'font-size="12.5"><tspan fill="{t["accent2"]}">{k}</tspan>'
            f'<tspan fill="{t["muted"]}">  ::  </tspan>'
            f'<tspan fill="{t["text"]}">{esc(v)}</tspan>{tail}</text>'
        )
        ly += 27
    blink_cursor = ""

    # stack preview chips (short — full stack lives in the README body)
    chips_y = rp_y + 196 + 30
    chip_label = (
        f'<text x="{rp_x}" y="{chips_y-12}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
        f'font-size="11" letter-spacing="2" fill="{t["accent"]}">STACK.PREVIEW</text>'
    )
    chip_items = ["JavaScript", "TypeScript", "Python", "React", "Node.js", "MongoDB", "OWASP"]
    chips = []
    cx = rp_x
    cy = chips_y
    for item in chip_items:
        cw = 13 + len(item) * 6.6
        if cx + cw > rp_x + rp_w:
            cx = rp_x
            cy += 30
        chips.append(
            f'<rect x="{cx}" y="{cy}" width="{cw}" height="22" rx="11" '
            f'fill="{t["panel2"]}" stroke="{t["border_bright"]}" stroke-width="1"/>'
            f'<text x="{cx+cw/2}" y="{cy+15}" text-anchor="middle" '
            f'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="10.5" '
            f'fill="{t["text"]}">{esc(item)}</text>'
        )
        cx += cw + 8
    chips.append(
        f'<text x="{cx+4}" y="{cy+15}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
        f'font-size="10.5" fill="{t["muted"]}">+more &#8594; see below</text>'
    )

    # quick links row
    ql_y = cy + 44
    ql_label = (
        f'<text x="{rp_x}" y="{ql_y-12}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
        f'font-size="11" letter-spacing="2" fill="{t["accent"]}">QUICK.LINKS</text>'
    )
    link_w = (rp_w - 16) / 3
    links = [
        ("GitHub", "https://github.com/kiran-devhub", "&#9095;"),
        ("Portfolio", "https://kkbportfolio.vercel.app/", "&#9670;"),
        ("Email", "mailto:kiran.devhub@gmail.com", "&#9993;"),
    ]
    link_svgs = []
    for i, (label, href, icon) in enumerate(links):
        lx = rp_x + i * (link_w + 8)
        link_svgs.append(build_quick_link(lx, ql_y, link_w, 34, label, href, t, icon))

    footer_y = H_TOTAL - 26
    footer = (
        f'<line x1="0" y1="{footer_y-16}" x2="{W}" y2="{footer_y-16}" stroke="{t["border"]}" stroke-width="1"/>'
        f'<text x="24" y="{footer_y+4}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
        f'font-size="12" fill="{t["accent"]}">kiran@devhub'
        f'<tspan fill="{t["muted"]}">:~$ </tspan>'
        f'<tspan fill="{t["text"]}">whoami</tspan>'
        f'<tspan fill="{t["accent"]}"> &#9608;'
        f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.45;0.5;0.95;1" '
        f'dur="1.1s" repeatCount="indefinite"/></tspan></text>'
        f'<text x="{W-24}" y="{footer_y+4}" text-anchor="end" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
        f'font-size="11" fill="{t["muted"]}">status: online</text>'
        f'<circle cx="{W-118}" cy="{footer_y}" r="4" fill="{t["accent3"] if theme_name=="dark" else t["accent"]}">'
        f'<animate attributeName="opacity" values="1;0.3;1" dur="1.6s" repeatCount="indefinite"/></circle>'
    )

    svg = f'''<svg width="{W}" height="{H_TOTAL}" viewBox="0 0 {W} {H_TOTAL}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" role="img" aria-label="Kiran Kumar Behera — Developer / Cybersecurity terminal profile banner">
<title>kiran-devhub profile banner ({theme_name})</title>
{defs}
{outer}
{titlebar}
{left_label}
{morph}
{right_label}
{info_frame}
{''.join(info_text)}
{blink_cursor}
{chip_label}
{''.join(chips)}
{ql_label}
{''.join(link_svgs)}
{footer}
</svg>'''
    return svg


def main():
    if not os.path.exists(SRC_PHOTO):
        print(f"ERROR: source photo not found at {SRC_PHOTO}", file=sys.stderr)
        sys.exit(1)

    portrait_dots, w, h = H.build_portrait_dots(SRC_PHOTO, CROP_BOX, WORK_W, WORK_H)
    dot_sets = {"portrait": (portrait_dots, w, h)}
    for name in ("shield", "code", "lock"):
        dot_sets[name] = H.build_icon_dots(name, WORK_W, WORK_H)

    os.makedirs(ASSETS, exist_ok=True)
    for theme_name in ("dark", "light"):
        svg = build_svg(theme_name, dot_sets)
        out_path = os.path.join(ASSETS, f"banner-{theme_name}.svg")
        with open(out_path, "w") as f:
            f.write(svg)
        print(f"wrote {out_path} ({len(svg)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
