"""
halftone.py
-----------
Turns a grayscale raster (a cropped photo, or a rendered icon glyph) into a
list of (x, y, r, opacity) dots — a controlled halftone / pointillist field.

Used for two things in this repo:
  1. The VISUAL.MAP portrait (kiran.png -> dots), tuned to keep facial
     structure legible at README scale (see build_portrait_dots).
  2. The three MORPH.ANIMATION target glyphs -- shield / code / lock --
     rendered as the same dot language so all four states in the morph
     loop feel like one consistent visual system (see build_icon_dots).

No dot data is invented from nothing: every dot's position/size comes from
sampling real pixel luminance of a real source raster (the photo, or a
locally rendered vector glyph) -- there is no placeholder/fake imagery here.
"""

from __future__ import annotations
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont


def _vignette_mask(w: int, h: int, cx_f=0.5, cy_f=0.42, rx_f=0.62, ry_f=0.66, power=0.8):
    """Soft elliptical weighting that favors the subject and lets the
    far background fall away into sparse dots instead of a hard crop line."""
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w * cx_f, h * cy_f
    rx, ry = w * rx_f, h * ry_f
    d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    mask = np.clip(1.25 - d, 0, 1) ** power
    return mask


def _sample_dots(gray_img: Image.Image, spacing: int, min_r: float, max_r: float,
                  gamma: float, cutoff: float, mask=None):
    arr = np.asarray(gray_img).astype(np.float32) / 255.0
    h, w = arr.shape
    if mask is None:
        mask = np.ones((h, w), dtype=np.float32)
    dots = []
    for y in range(0, h, spacing):
        row = arr[y]
        mrow = mask[y]
        for x in range(0, w, spacing):
            dark = 1.0 - row[x]
            weight = (dark ** gamma) * mrow[x]
            if weight < cutoff:
                continue
            r = min_r + (max_r - min_r) * weight
            op = min(1.0, 0.30 + weight)
            dots.append((round(x, 1), round(y, 1), round(r, 2), round(op, 2)))
    return dots


def build_portrait_dots(src_path: str, crop_box, work_w=260, work_h=312,
                         spacing=4, min_r=0.35, max_r=2.15, gamma=1.35, cutoff=0.11):
    """crop_box: (left, top, right, bottom) in the *source* image's own pixel
    coordinates. Returns (dots, w, h) where w/h are the working canvas size
    the dot coordinates are expressed in (so the SVG can scale/position it)."""
    im = Image.open(src_path).convert("RGB")
    im = im.crop(crop_box).resize((work_w, work_h), Image.LANCZOS)
    gray = ImageOps.grayscale(im)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    mask = _vignette_mask(work_w, work_h)
    dots = _sample_dots(gray, spacing, min_r, max_r, gamma, cutoff, mask)
    return dots, work_w, work_h


def _glyph_canvas(draw_fn, w=260, h=312):
    """Render a simple vector glyph (shield / lock) with PIL ImageDraw onto a
    white-on-black canvas of the same working size as the portrait, so every
    morph state shares one coordinate system."""
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    draw_fn(d, w, h)
    return im


def _shield_glyph(w, h):
    def draw(d: ImageDraw.ImageDraw, w, h):
        cx = w * 0.5
        top = h * 0.16
        bot = h * 0.82
        half = w * 0.30
        pts = [
            (cx, top),
            (cx + half, top + (bot - top) * 0.16),
            (cx + half, top + (bot - top) * 0.55),
            (cx, bot),
            (cx - half, top + (bot - top) * 0.55),
            (cx - half, top + (bot - top) * 0.16),
        ]
        d.polygon(pts, fill=255)
        # inner cutout to give the shield a rim
        inset = 0.14
        pts_in = []
        for (x, y) in pts:
            pts_in.append((cx + (x - cx) * (1 - inset), cy_scale(y, top, bot, inset)))
        d.polygon(pts_in, fill=70)
        # checkmark
        d.line([(cx - half * 0.42, h * 0.46), (cx - half * 0.08, h * 0.60),
                (cx + half * 0.46, h * 0.30)], fill=255, width=max(2, int(w * 0.045)))
    return _glyph_canvas(draw, w, h)


def cy_scale(y, top, bot, inset):
    mid = (top + bot) / 2
    return mid + (y - mid) * (1 - inset)


def _lock_glyph(w, h):
    def draw(d: ImageDraw.ImageDraw, w, h):
        body_w = w * 0.52
        body_h = h * 0.40
        bx0 = (w - body_w) / 2
        by0 = h * 0.48
        bx1 = bx0 + body_w
        by1 = by0 + body_h
        d.rounded_rectangle([bx0, by0, bx1, by1], radius=w * 0.05, fill=255)
        # shackle
        shackle_w = body_w * 0.62
        sx0 = (w - shackle_w) / 2
        sx1 = sx0 + shackle_w
        sy0 = h * 0.18
        sy1 = by0 + h * 0.05
        d.arc([sx0, sy0, sx1, sy1 + (sx1 - sx0) * 0.15], start=180, end=360,
              fill=255, width=max(3, int(w * 0.07)))
        d.line([sx0, (sy0 + sy1) / 2, sx0, sy1], fill=255, width=max(3, int(w * 0.07)))
        d.line([sx1, (sy0 + sy1) / 2, sx1, sy1], fill=255, width=max(3, int(w * 0.07)))
        # keyhole
        khx, khy = w * 0.5, by0 + body_h * 0.42
        r = w * 0.045
        d.ellipse([khx - r, khy - r, khx + r, khy + r], fill=0)
        d.polygon([(khx - r * 0.6, khy), (khx + r * 0.6, khy),
                   (khx + r * 0.9, by1 - h * 0.05)], fill=0)
    return _glyph_canvas(draw, w, h)


def _code_glyph(w, h):
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", int(h * 0.42)
        )
    except OSError:
        font = ImageFont.load_default()
    text = "</>"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((w / 2 - tw / 2 - bbox[0], h / 2 - th / 2 - bbox[1]), text, fill=255, font=font)
    return im


_GLYPHS = {"shield": _shield_glyph, "lock": _lock_glyph, "code": _code_glyph}


def build_icon_dots(name: str, work_w=260, work_h=312, spacing=5,
                     min_r=0.4, max_r=2.0, gamma=1.0, cutoff=0.2):
    """Renders one of 'shield' | 'code' | 'lock' as a dot field in the same
    coordinate space as the portrait, so the SVG can cross-fade between
    them without any jump in scale or alignment."""
    gray = _GLYPHS[name](work_w, work_h)
    mask = _vignette_mask(work_w, work_h, rx_f=0.9, ry_f=0.9, power=1.0)
    # glyphs are already white-on-black; treat *brightness* as the ink weight
    arr = np.asarray(gray).astype(np.float32) / 255.0
    inverted = Image.fromarray(np.uint8((1 - arr) * 255))
    dots = _sample_dots(inverted, spacing, min_r, max_r, gamma, cutoff, mask)
    return dots, work_w, work_h
