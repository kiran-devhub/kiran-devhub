"""Shared theme tokens + tiny SVG helpers for cards.py / languages.py / radar.py.

Kept intentionally separate from scripts/banner/generate.py (which has its
own richer layout code for the hero) so each script can run standalone in
CI without importing the whole banner pipeline.
"""

FONT = "ui-monospace,SFMono-Regular,Consolas,monospace"

THEMES = {
    "dark": dict(
        bg="#05080c", panel="#0b141a", panel2="#0d1720",
        border="#173039", border_bright="#2dd8c8",
        text="#dff7f1", muted="#5f8a86",
        accent="#38f2d8", accent2="#ff3e7f", accent3="#ffcf5c",
        track="#152a30",
    ),
    "light": dict(
        bg="#eef3f4", panel="#ffffff", panel2="#f5f9f9",
        border="#c7dbdc", border_bright="#0f8b7d",
        text="#0b1c1c", muted="#4d6567",
        accent="#0f8b7d", accent2="#c81361", accent3="#a56a00",
        track="#dcecec",
    ),
}


def esc(s: str) -> str:
    return (
        str(s).replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )


def card_shell(w, h, theme_name, title):
    t = THEMES[theme_name]
    return (
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="14" '
        f'fill="{t["bg"]}" stroke="{t["border_bright"]}" stroke-width="1.4"/>'
        f'<circle cx="20" cy="20" r="4.5" fill="#ff5f57"/>'
        f'<circle cx="34" cy="20" r="4.5" fill="#febc2e"/>'
        f'<circle cx="48" cy="20" r="4.5" fill="#28c840"/>'
        f'<text x="{w/2}" y="24" text-anchor="middle" font-family="{FONT}" '
        f'font-size="11" fill="{t["muted"]}">{esc(title)}</text>'
        f'<line x1="0" y1="34" x2="{w}" y2="34" stroke="{t["border"]}" stroke-width="1"/>'
    )


def placeholder_note(w, h, theme_name, message):
    t = THEMES[theme_name]
    return (
        f'<text x="{w/2}" y="{h/2-6}" text-anchor="middle" font-family="{FONT}" '
        f'font-size="12" fill="{t["muted"]}">{esc(message)}</text>'
        f'<text x="{w/2}" y="{h/2+14}" text-anchor="middle" font-family="{FONT}" '
        f'font-size="10.5" fill="{t["accent"]}">populated automatically by .github/workflows/profile.yml</text>'
    )


def wrap_svg(w, h, theme_name, body, title):
    t = THEMES[theme_name]
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(title)}">'
        f'<title>{esc(title)}</title>{body}</svg>'
    )
