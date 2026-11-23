#!/usr/bin/env python3
"""Generates all original artwork and audio for this game (no third-party
assets): app icon, adaptive icon, splash, store feature graphic, store
screenshots frames (TR + EN) and sound effects.

Run locally or in CI:  pip install pillow && python tool/generate_assets.py
"""
import math
import os
import random
import struct
import wave

from PIL import Image, ImageDraw, ImageFilter, ImageFont

MOTIF = "brain"
TITLE = {"tr": "Zihin Antrenmanı", "en": "Brain Training"}
TAGLINE = {"tr": "Hafıza, dikkat, hız ve mantık", "en": "Memory, attention, speed and logic"}
BG = "#2A2D4A"
ACCENT = "#7FD1B9"
FEATURES = {
    "tr": ["Egzersiz başına 100.000 bölüm", "10 kısa zihin egzersizi", "Her gün yeni program", "Görevler ve başarımlar"],
    "en": ["100,000 levels per exercise", "10 short brain exercises", "A new plan every day", "Missions and achievements"],
}
PALETTE = ["#EF5350", "#42A5F5", "#66BB6A", "#FFCA28", "#AB47BC", "#26C6DA", "#FF7043", "#EC407A"]


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def font(size, bold=True):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def gradient(w, h, top, bottom):
    img = Image.new("RGB", (w, h), top)
    d = ImageDraw.Draw(img)
    a, b = hex2rgb(top), hex2rgb(bottom)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))
    return img


def rr(d, box, r, fill, outline=None, width=0):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def tile(d, x, y, s, color, r=None):
    r = r if r is not None else s * 0.18
    rr(d, (x, y, x + s, y + s), r, color)
    hl = tuple(min(255, c + 60) for c in hex2rgb(color))
    rr(d, (x + s * 0.12, y + s * 0.1, x + s * 0.88, y + s * 0.38), r * 0.6, hl)


# ---------------------------------------------------------------- motifs
def m_blocks(d, cx, cy, S, rnd):
    s = S / 4.4
    shape = [(0, 0), (1, 0), (2, 0), (0, 1), (2, 2), (1, 2), (2, 1), (3, 3), (0, 3), (1, 3)]
    for i, (gx, gy) in enumerate(shape):
        tile(d, cx - 2 * s + gx * s * 1.05, cy - 2 * s + gy * s * 1.05, s * 0.98, PALETTE[i % 5])


def m_bottles(d, cx, cy, S, rnd):
    w, h = S * 0.2, S * 0.78
    for b in range(3):
        x = cx - S * 0.36 + b * S * 0.27
        y = cy - h / 2
        layers = rnd.sample(PALETTE[:6], 4)
        for i, c in enumerate(layers):
            ly = y + h - (i + 1) * h * 0.22
            rr(d, (x, ly, x + w, ly + h * 0.22), w * 0.2 if i == 0 else 4, c)
        rr(d, (x - 6, y - 6, x + w + 6, y + h + 6), w * 0.35, None, "white", max(4, int(S * 0.02)))


def m_balls(d, cx, cy, S, rnd):
    w, h = S * 0.22, S * 0.8
    for b in range(3):
        x = cx - S * 0.38 + b * S * 0.28
        y = cy - h / 2
        rr(d, (x, y, x + w, y + h), w / 2, (255, 255, 255, 60), "white", max(4, int(S * 0.02)))
        cols = rnd.sample(PALETTE[:6], 4)
        for i, c in enumerate(cols):
            r = w * 0.4
            by = y + h - r - 8 - i * (2 * r + 4)
            d.ellipse((x + w / 2 - r, by - r, x + w / 2 + r, by + r), fill=c)
            d.ellipse((x + w / 2 - r * 0.5, by - r * 0.7, x + w / 2 - r * 0.05, by - r * 0.25), fill="white")


def m_2048(d, cx, cy, S, rnd):
    s = S / 2.2
    vals = [2048, 512, 64, 8]
    cols = ["#EDC22E", "#F67C5F", "#F2B179", "#EDE0C8"]
    for i in range(4):
        x = cx - s - 6 + (i % 2) * (s + 12)
        y = cy - s - 6 + (i // 2) * (s + 12)
        rr(d, (x, y, x + s, y + s), s * 0.12, cols[i])
        f = font(int(s * (0.28 if vals[i] > 999 else 0.4)))
        t = str(vals[i])
        tw, th = d.textbbox((0, 0), t, font=f)[2:]
        d.text((x + (s - tw) / 2, y + (s - th) / 2 - s * 0.04), t, fill="white" if i < 3 else "#776E65", font=f)


def m_sudoku(d, cx, cy, S, rnd):
    s = S * 0.8
    x0, y0 = cx - s / 2, cy - s / 2
    rr(d, (x0, y0, x0 + s, y0 + s), s * 0.06, "white")
    for i in range(10):
        w = 6 if i % 3 == 0 else 2
        d.line([(x0 + i * s / 9, y0), (x0 + i * s / 9, y0 + s)], fill="#37474F", width=w)
        d.line([(x0, y0 + i * s / 9), (x0 + s, y0 + i * s / 9)], fill="#37474F", width=w)
    f = font(int(s / 13))
    for k in range(18):
        gx, gy = rnd.randrange(9), rnd.randrange(9)
        t = str(rnd.randrange(1, 10))
        d.text((x0 + gx * s / 9 + s / 30, y0 + gy * s / 9 + s / 60), t, fill=ACCENT if k % 3 == 0 else "#263238", font=f)


def m_jigsaw(d, cx, cy, S, rnd):
    s = S * 0.36
    for i, c in enumerate(PALETTE[:4]):
        x = cx - s + (i % 2) * s
        y = cy - s + (i // 2) * s
        rr(d, (x + 4, y + 4, x + s - 4, y + s - 4), s * 0.08, c)
        r = s * 0.16
        if i % 2 == 0:
            d.ellipse((x + s - 4 - r, y + s / 2 - r, x + s - 4 + r, y + s / 2 + r), fill=c)
        if i < 2:
            d.ellipse((x + s / 2 - r, y + s - 4 - r, x + s / 2 + r, y + s - 4 + r), fill=c)


def m_nonogram(d, cx, cy, S, rnd):
    n = 6
    s = S * 0.8 / n
    pic = ["011110", "111111", "110011", "111111", "011110", "001100"]
    x0, y0 = cx - s * n / 2, cy - s * n / 2
    for y in range(n):
        for x in range(n):
            fill = "#263238" if pic[y][x] == "1" else "white"
            d.rectangle((x0 + x * s + 2, y0 + y * s + 2, x0 + (x + 1) * s - 2, y0 + (y + 1) * s - 2), fill=fill)


def m_unblock(d, cx, cy, S, rnd):
    s = S * 0.8
    x0, y0 = cx - s / 2, cy - s / 2
    rr(d, (x0, y0, x0 + s, y0 + s), s * 0.05, "#8D6E63")
    c = s / 6
    blocks = [(0, 2, 2, 1, "#E53935"), (3, 0, 1, 3, "#FFB74D"), (4, 3, 2, 1, "#FFB74D"), (1, 4, 1, 2, "#FFB74D"), (5, 0, 1, 2, "#FFB74D")]
    for (x, y, w, h, col) in blocks:
        rr(d, (x0 + x * c + 5, y0 + y * c + 5, x0 + (x + w) * c - 5, y0 + (y + h) * c - 5), c * 0.2, col)
    d.rectangle((x0 + s - 6, y0 + 2 * c + 8, x0 + s + 10, y0 + 3 * c - 8), fill="#FFEB3B")


def m_numbers(d, cx, cy, S, rnd):
    s = S * 0.8 / 4
    x0, y0 = cx - 2 * s, cy - 2 * s
    f = font(int(s * 0.55))
    nums = [3, 7, 5, 5, 1, 9, 4, 6, 8, 2, 2, 8, 6, 4, 9, 1]
    for i, v in enumerate(nums):
        x, y = x0 + (i % 4) * s, y0 + (i // 4) * s
        hl = i in (2, 3, 0, 1) and i in (2, 3)
        rr(d, (x + 4, y + 4, x + s - 4, y + s - 4), s * 0.2, ACCENT if hl else "white")
        t = str(v)
        tw, th = d.textbbox((0, 0), t, font=f)[2:]
        d.text((x + (s - tw) / 2, y + (s - th) / 2 - s * 0.05), t, fill="#263238", font=f)


def m_dots(d, cx, cy, S, rnd):
    n = 5
    s = S * 0.8 / n
    x0, y0 = cx - s * n / 2, cy - s * n / 2
    paths = [
        ("#EF5350", [(0, 0), (1, 0), (2, 0), (2, 1)]),
        ("#42A5F5", [(0, 1), (0, 2), (0, 3), (0, 4), (1, 4)]),
        ("#66BB6A", [(3, 0), (4, 0), (4, 1), (4, 2)]),
        ("#FFCA28", [(1, 1), (1, 2), (2, 2), (3, 2), (3, 1)]),
    ]
    for col, pts in paths:
        for a, b in zip(pts, pts[1:]):
            d.line([(x0 + (a[0] + .5) * s, y0 + (a[1] + .5) * s), (x0 + (b[0] + .5) * s, y0 + (b[1] + .5) * s)], fill=col, width=int(s * 0.38))
        for p in (pts[0], pts[-1]):
            r = s * 0.34
            d.ellipse((x0 + (p[0] + .5) * s - r, y0 + (p[1] + .5) * s - r, x0 + (p[0] + .5) * s + r, y0 + (p[1] + .5) * s + r), fill=col)


def m_verse(d, cx, cy, S, rnd):
    s = S * 0.42
    # four quadrants: lights, pipe, number, card
    boxes = [(cx - s - 6, cy - s - 6), (cx + 6, cy - s - 6), (cx - s - 6, cy + 6), (cx + 6, cy + 6)]
    rr(d, (*boxes[0], boxes[0][0] + s, boxes[0][1] + s), s * 0.15, "#FFD60A")
    rr(d, (*boxes[1], boxes[1][0] + s, boxes[1][1] + s), s * 0.15, "#1B263B")
    x, y = boxes[1]
    d.line([(x + s / 2, y), (x + s / 2, y + s / 2), (x + s, y + s / 2)], fill=ACCENT, width=int(s * 0.18))
    rr(d, (*boxes[2], boxes[2][0] + s, boxes[2][1] + s), s * 0.15, PALETTE[2])
    f = font(int(s * 0.55))
    x, y = boxes[2]
    tw, th = d.textbbox((0, 0), "15", font=f)[2:]
    d.text((x + (s - tw) / 2, y + (s - th) / 2 - s * 0.05), "15", fill="white", font=f)
    rr(d, (*boxes[3], boxes[3][0] + s, boxes[3][1] + s), s * 0.15, "#3A0CA3")
    x, y = boxes[3]
    tw, th = d.textbbox((0, 0), "?", font=f)[2:]
    d.text((x + (s - tw) / 2, y + (s - th) / 2 - s * 0.05), "?", fill="white", font=f)


def m_snake(d, cx, cy, S, rnd):
    s = S / 7
    pts = [(0, 3), (1, 3), (2, 3), (2, 2), (2, 1), (3, 1), (4, 1), (4, 2), (4, 3), (4, 4), (5, 4)]
    for i, (gx, gy) in enumerate(pts):
        col = PALETTE[1] if i < len(pts) - 1 else ACCENT
        rr(d, (cx - 3 * s + gx * s, cy - 3 * s + gy * s, cx - 2 * s + gx * s - 4, cy - 2 * s + gy * s - 4), s * 0.3, col)
    hx, hy = cx - 3 * s + 5 * s, cy - 3 * s + 4 * s
    d.ellipse((hx + s * 0.55, hy + s * 0.2, hx + s * 0.8, hy + s * 0.45), fill="white")
    r = s * 0.35
    d.ellipse((cx + 1.2 * s - r, cy - 2.2 * s - r, cx + 1.2 * s + r, cy - 2.2 * s + r), fill="#FF595E")


def m_bricks(d, cx, cy, S, rnd):
    w, h = S * 0.19, S * 0.09
    for row in range(4):
        for col in range(5):
            x = cx - 2.5 * w + col * w
            y = cy - S * 0.4 + row * (h + 6)
            rr(d, (x + 3, y, x + w - 3, y + h), 8, PALETTE[(row + col) % 5])
    r = S * 0.05
    d.ellipse((cx - r, cy + S * 0.12 - r, cx + r, cy + S * 0.12 + r), fill="white")
    rr(d, (cx - S * 0.18, cy + S * 0.32, cx + S * 0.18, cy + S * 0.38), 10, ACCENT)


def m_bubbles(d, cx, cy, S, rnd):
    r = S * 0.1
    for row in range(3):
        for col in range(4 - row % 2):
            x = cx - 1.5 * 2 * r + col * 2 * r + (r if row % 2 else 0)
            y = cy - S * 0.3 + row * r * 1.75
            c = PALETTE[(row * 3 + col) % 5]
            d.ellipse((x - r, y - r, x + r, y + r), fill=c)
            d.ellipse((x - r * 0.5, y - r * 0.6, x - r * 0.1, y - r * 0.2), fill="white")
    y = cy + S * 0.32
    d.ellipse((cx - r * 1.2, y - r * 1.2, cx + r * 1.2, y + r * 1.2), fill=ACCENT)
    d.line([(cx, y - r * 1.3), (cx + S * 0.1, cy)], fill="white", width=6)


def m_invaders(d, cx, cy, S, rnd):
    px = S / 16
    alien = ["00100000100", "00010001000", "00111111100", "01101110110", "11111111111", "10111111101", "10100000101", "00011011000"]
    x0, y0 = cx - 5.5 * px, cy - S * 0.38
    for y, line in enumerate(alien):
        for x, ch in enumerate(line):
            if ch == "1":
                d.rectangle((x0 + x * px, y0 + y * px, x0 + (x + 1) * px - 2, y0 + (y + 1) * px - 2), fill=PALETTE[1])
    sy = cy + S * 0.3
    d.polygon([(cx, sy - S * 0.12), (cx + S * 0.12, sy + S * 0.06), (cx - S * 0.12, sy + S * 0.06)], fill=ACCENT)
    d.rectangle((cx - 4, cy - S * 0.05, cx + 4, cy + S * 0.1), fill="#FFFF3F")


def m_maze(d, cx, cy, S, rnd):
    s = S * 0.8
    x0, y0 = cx - s / 2, cy - s / 2
    w = int(S * 0.03)
    walls = [((0, 0), (1, 0)), ((0, 0), (0, 1)), ((1, 0), (1, 1)), ((0, 1), (1, 1)), ((0.25, 0.25), (0.75, 0.25)),
             ((0.25, 0.25), (0.25, 0.5)), ((0.75, 0.5), (0.75, 0.75)), ((0.25, 0.75), (0.75, 0.75))]
    for a, b in walls:
        d.line([(x0 + a[0] * s, y0 + a[1] * s), (x0 + b[0] * s, y0 + b[1] * s)], fill=PALETTE[3], width=w)
    for i in range(5):
        r = S * 0.02
        x = x0 + s * (0.15 + i * 0.12)
        d.ellipse((x - r, cy - r, x + r, cy + r), fill="white")
    r = S * 0.13
    d.pieslice((cx + S * 0.12 - r, cy - r, cx + S * 0.12 + r, cy + r), 30, 330, fill=ACCENT)


def m_flappy(d, cx, cy, S, rnd):
    pw = S * 0.18
    for x, gap in ((cx - S * 0.32, cy - S * 0.1), (cx + S * 0.2, cy + S * 0.12)):
        d.rectangle((x, cy - S * 0.45, x + pw, gap - S * 0.14), fill="#52B788")
        d.rectangle((x, gap + S * 0.14, x + pw, cy + S * 0.45), fill="#52B788")
    r = S * 0.1
    bx, by = cx - S * 0.04, cy - S * 0.02
    d.ellipse((bx - r * 1.2, by - r, bx + r * 1.2, by + r), fill=ACCENT)
    d.ellipse((bx + r * 0.3, by - r * 0.6, bx + r * 0.8, by - r * 0.1), fill="white")
    d.polygon([(bx + r * 1.1, by), (bx + r * 1.7, by + r * 0.2), (bx + r * 1.1, by + r * 0.4)], fill="#FF9F1C")


def m_bounce(d, cx, cy, S, rnd):
    gy = cy + S * 0.3
    d.rectangle((cx - S * 0.45, gy, cx + S * 0.45, gy + S * 0.08), fill=PALETTE[3])
    for i in range(3):
        x = cx + S * 0.05 + i * S * 0.1
        d.polygon([(x, gy), (x + S * 0.05, gy - S * 0.12), (x + S * 0.1, gy)], fill="#E63946")
    r = S * 0.12
    d.ellipse((cx - S * 0.2 - r, cy - S * 0.15 - r, cx - S * 0.2 + r, cy - S * 0.15 + r), fill=ACCENT)
    for k in range(3):
        d.arc((cx - S * 0.4 + k * S * 0.06, cy - S * 0.05, cx - S * 0.1, cy + S * 0.3), 200, 260, fill="white", width=4)


def m_stack(d, cx, cy, S, rnd):
    h = S * 0.1
    for i in range(6):
        w = S * (0.6 - i * 0.04)
        off = (i % 2) * S * 0.03
        y = cy + S * 0.35 - i * (h + 4)
        rr(d, (cx - w / 2 + off, y - h, cx + w / 2 + off, y), 6, PALETTE[i % 5])
    rr(d, (cx - S * 0.2 + S * 0.15, cy - S * 0.42, cx + S * 0.2 + S * 0.15, cy - S * 0.42 + h), 6, ACCENT)


def m_crossy(d, cx, cy, S, rnd):
    lanes = [("#74C69D", None), ("#495057", PALETTE[0]), ("#00B4D8", "#8B5E34"), ("#74C69D", None)]
    lh = S * 0.2
    for i, (bg, obj) in enumerate(lanes):
        y = cy - S * 0.4 + i * lh
        d.rectangle((cx - S * 0.45, y, cx + S * 0.45, y + lh), fill=bg)
        if obj:
            ox = cx - S * 0.3 + i * S * 0.15
            rr(d, (ox, y + lh * 0.2, ox + S * 0.25, y + lh * 0.8), 10, obj)
    r = S * 0.07
    y = cy + S * 0.3
    rr(d, (cx - r, y - r, cx + r, y + r), 8, "white")
    d.rectangle((cx - r * 0.3, y - r * 1.4, cx + r * 0.3, y - r), fill="#E63946")


def _house(d, x, y, w, h, wall, roof):
    d.rectangle((x - w / 2, y - h, x + w / 2, y), fill=wall)
    d.polygon([(x - w * 0.62, y - h), (x, y - h - w * 0.5), (x + w * 0.62, y - h)], fill=roof)


def m_td(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.45, cy + S * 0.05, cx + S * 0.45, cy + S * 0.2), fill="#DDB892")
    tw = S * 0.22
    d.rectangle((cx - tw / 2, cy - S * 0.35, cx + tw / 2, cy + S * 0.1), fill="#6C757D")
    for i in range(3):
        x = cx - tw / 2 + i * tw * 0.4
        d.rectangle((x, cy - S * 0.43, x + tw * 0.2, cy - S * 0.35), fill="#6C757D")
    d.ellipse((cx - S * 0.06, cy - S * 0.25, cx + S * 0.06, cy - S * 0.13), fill=ACCENT)
    for i, col in enumerate(("#E63946", "#FFB703", "#E63946")):
        x = cx - S * 0.38 + i * S * 0.1
        d.ellipse((x - S * 0.04, cy + S * 0.08, x + S * 0.04, cy + S * 0.16), fill=col)
    d.line((cx, cy - S * 0.19, cx - S * 0.3, cy + S * 0.12), fill=ACCENT, width=max(3, int(S * 0.015)))


def m_civ(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.45, cy + S * 0.25, cx + S * 0.45, cy + S * 0.33), fill="#6A994E")
    _house(d, cx - S * 0.25, cy + S * 0.25, S * 0.2, S * 0.15, "#B08968", "#7F5539")
    _house(d, cx + S * 0.25, cy + S * 0.25, S * 0.2, S * 0.15, "#B08968", "#7F5539")
    d.polygon([(cx - S * 0.12, cy + S * 0.25), (cx, cy - S * 0.35), (cx + S * 0.12, cy + S * 0.25)], fill=ACCENT)
    d.ellipse((cx + S * 0.2, cy - S * 0.4, cx + S * 0.36, cy - S * 0.24), fill="#FFD166")


def m_empire(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.3, cy - S * 0.1, cx + S * 0.3, cy + S * 0.3), fill="#6C757D")
    for i in range(5):
        x = cx - S * 0.3 + i * S * 0.13
        d.rectangle((x, cy - S * 0.18, x + S * 0.08, cy - S * 0.1), fill="#6C757D")
    d.rectangle((cx - S * 0.06, cy + S * 0.1, cx + S * 0.06, cy + S * 0.3), fill="#343A40")
    d.line((cx, cy - S * 0.18, cx, cy - S * 0.45), fill="white", width=max(3, int(S * 0.012)))
    d.polygon([(cx, cy - S * 0.45), (cx + S * 0.2, cy - S * 0.38), (cx, cy - S * 0.31)], fill=ACCENT)


def m_factory(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.4, cy, cx + S * 0.4, cy + S * 0.3), fill="#495057")
    for i in range(3):
        x = cx - S * 0.4 + i * S * 0.27
        d.polygon([(x, cy), (x + S * 0.27, cy - S * 0.12), (x + S * 0.27, cy)], fill="#6C757D")
    d.rectangle((cx + S * 0.22, cy - S * 0.42, cx + S * 0.32, cy), fill="#343A40")
    d.ellipse((cx + S * 0.2, cy - S * 0.55, cx + S * 0.36, cy - S * 0.42), fill="#ADB5BD")
    r = S * 0.11
    d.ellipse((cx - S * 0.12 - r, cy + S * 0.15 - r, cx - S * 0.12 + r, cy + S * 0.15 + r), fill=ACCENT)
    d.ellipse((cx - S * 0.12 - r * 0.4, cy + S * 0.15 - r * 0.4, cx - S * 0.12 + r * 0.4, cy + S * 0.15 + r * 0.4), fill="#495057")


def m_city(d, cx, cy, S, rnd):
    hs = [0.5, 0.75, 0.4, 0.9, 0.6]
    w = S * 0.16
    for i, h in enumerate(hs):
        x = cx - S * 0.42 + i * (w + S * 0.02)
        col = PALETTE[i % len(PALETTE)]
        d.rectangle((x, cy + S * 0.35 - S * h * 0.7, x + w, cy + S * 0.35), fill=col)
        for k in range(int(h * 5)):
            yy = cy + S * 0.35 - S * h * 0.7 + S * 0.05 + k * S * 0.09
            d.rectangle((x + w * 0.2, yy, x + w * 0.4, yy + S * 0.04), fill="#FFF3B0")
            d.rectangle((x + w * 0.6, yy, x + w * 0.8, yy + S * 0.04), fill="#FFF3B0")


def m_farm(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.45, cy + S * 0.15, cx + S * 0.45, cy + S * 0.35), fill="#8AB17D")
    for i in range(6):
        x = cx - S * 0.4 + i * S * 0.15
        d.ellipse((x, cy + S * 0.18, x + S * 0.08, cy + S * 0.26), fill="#FFD166")
    _house(d, cx - S * 0.12, cy + S * 0.15, S * 0.34, S * 0.25, "#C1121F", "#780000")
    d.rectangle((cx - S * 0.18, cy - S * 0.02, cx - S * 0.06, cy + S * 0.15), fill="white")
    d.rectangle((cx + S * 0.18, cy - S * 0.25, cx + S * 0.3, cy + S * 0.15), fill="#ADB5BD")
    d.ellipse((cx + S * 0.18, cy - S * 0.31, cx + S * 0.3, cy - S * 0.19), fill="#ADB5BD")


def m_restaurant(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.4, cy - S * 0.05, cx + S * 0.4, cy + S * 0.3), fill="white")
    d.ellipse((cx - S * 0.28, cy + S * 0.02, cx + S * 0.28, cy + S * 0.23), fill="#F1FAEE")
    d.ellipse((cx - S * 0.2, cy - S * 0.08, cx + S * 0.2, cy + S * 0.08), fill="#E9C46A")
    d.rectangle((cx - S * 0.21, cy + S * 0.0, cx + S * 0.21, cy + S * 0.05), fill="#6A040F")
    d.ellipse((cx - S * 0.2, cy + S * 0.02, cx + S * 0.2, cy + S * 0.14), fill="#E9C46A")
    d.ellipse((cx - S * 0.12, cy - S * 0.45, cx + S * 0.12, cy - S * 0.25), fill="white")
    d.rectangle((cx - S * 0.09, cy - S * 0.3, cx + S * 0.09, cy - S * 0.17), fill="white")


def m_airport(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.45, cy + S * 0.22, cx + S * 0.45, cy + S * 0.32), fill="#495057")
    for i in range(5):
        x = cx - S * 0.4 + i * S * 0.18
        d.rectangle((x, cy + S * 0.26, x + S * 0.08, cy + S * 0.28), fill="white")
    d.polygon([(cx - S * 0.4, cy), (cx + S * 0.35, cy - S * 0.08), (cx + S * 0.42, cy - S * 0.02), (cx - S * 0.35, cy + S * 0.06)], fill="white")
    d.polygon([(cx - S * 0.02, cy - S * 0.03), (cx + S * 0.12, cy - S * 0.3), (cx + S * 0.2, cy - S * 0.3), (cx + S * 0.12, cy - S * 0.04)], fill=ACCENT)
    d.polygon([(cx - S * 0.02, cy + S * 0.02), (cx + S * 0.06, cy + S * 0.2), (cx + S * 0.14, cy + S * 0.2), (cx + S * 0.12, cy)], fill=ACCENT)
    d.polygon([(cx - S * 0.38, cy), (cx - S * 0.42, cy - S * 0.15), (cx - S * 0.32, cy - S * 0.15), (cx - S * 0.28, cy)], fill=ACCENT)


def m_hotel(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.25, cy - S * 0.38, cx + S * 0.25, cy + S * 0.35), fill="#5A189A")
    for r in range(6):
        for k in range(3):
            x = cx - S * 0.2 + k * S * 0.15
            y = cy - S * 0.32 + r * S * 0.1
            d.rectangle((x, y, x + S * 0.08, y + S * 0.06), fill="#FFD166" if (r + k) % 3 else "#3C096C")
    d.rectangle((cx - S * 0.08, cy + S * 0.22, cx + S * 0.08, cy + S * 0.35), fill=ACCENT)
    for i in range(5):
        x = cx - S * 0.2 + i * S * 0.1
        d.polygon([(x, cy - S * 0.44), (x + S * 0.02, cy - S * 0.48), (x + S * 0.04, cy - S * 0.44)], fill="#FFD60A")


def m_colony(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.5, cy + S * 0.15, cx + S * 0.5, cy + S * 0.7), fill="#9C6644")
    d.pieslice((cx - S * 0.3, cy - S * 0.2, cx + S * 0.3, cy + S * 0.4), 180, 360, fill=(142, 202, 230, 200))
    d.pieslice((cx + S * 0.12, cy, cx + S * 0.42, cy + S * 0.3), 180, 360, fill=(142, 202, 230, 200))
    d.rectangle((cx - S * 0.05, cy - S * 0.42, cx + S * 0.05, cy - S * 0.12), fill="white")
    d.polygon([(cx - S * 0.05, cy - S * 0.42), (cx, cy - S * 0.5), (cx + S * 0.05, cy - S * 0.42)], fill=ACCENT)
    for i in range(12):
        x, y = rnd.uniform(cx - S * 0.45, cx + S * 0.45), rnd.uniform(cy - S * 0.45, cy - S * 0.2)
        d.ellipse((x, y, x + 4, y + 4), fill="white")


def _car(d, x, y, w, h, col, up=True):
    rr(d, (x - w / 2, y - h / 2, x + w / 2, y + h / 2), int(w * 0.3), col)
    gy = y - h * 0.22 if up else y + h * 0.1
    rr(d, (x - w * 0.36, gy, x + w * 0.36, gy + h * 0.16), int(w * 0.1), "#BDE0FE")
    for sx in (-1, 1):
        d.rectangle((x + sx * w * 0.5 - w * 0.08, y - h * 0.36, x + sx * w * 0.5 + w * 0.08, y - h * 0.18), fill="#212529")
        d.rectangle((x + sx * w * 0.5 - w * 0.08, y + h * 0.18, x + sx * w * 0.5 + w * 0.08, y + h * 0.36), fill="#212529")


def _road(d, cx, cy, S, lanes=3, col="#495057"):
    d.rectangle((cx - S * 0.42, cy - S * 0.48, cx + S * 0.42, cy + S * 0.48), fill=col)
    for i in range(1, lanes):
        x = cx - S * 0.42 + i * S * 0.84 / lanes
        for k in range(6):
            y = cy - S * 0.46 + k * S * 0.17
            d.rectangle((x - S * 0.008, y, x + S * 0.008, y + S * 0.09), fill="white")


def m_traffic(d, cx, cy, S, rnd):
    _road(d, cx, cy, S, 3)
    _car(d, cx - S * 0.28, cy - S * 0.22, S * 0.17, S * 0.3, PALETTE[1])
    _car(d, cx + S * 0.28, cy - S * 0.05, S * 0.17, S * 0.3, PALETTE[3])
    _car(d, cx, cy + S * 0.25, S * 0.19, S * 0.33, ACCENT)


def m_parking(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.45, cy - S * 0.45, cx + S * 0.45, cy + S * 0.45), fill="#6C757D")
    for i in range(5):
        x = cx - S * 0.45 + i * S * 0.225
        d.rectangle((x - 2, cy - S * 0.45, x + 2, cy - S * 0.05), fill="white")
    _car(d, cx - S * 0.34, cy - S * 0.25, S * 0.14, S * 0.3, PALETTE[0])
    _car(d, cx + S * 0.11, cy - S * 0.25, S * 0.14, S * 0.3, PALETTE[2])
    d.rectangle((cx - S * 0.2, cy - S * 0.43, cx - S * 0.03, cy - S * 0.07), outline="#FFD60A", width=max(3, int(S * 0.012)))
    _car(d, cx - S * 0.11, cy + S * 0.22, S * 0.14, S * 0.3, ACCENT)
    f = font(int(S * 0.14))
    d.text((cx + S * 0.25, cy + S * 0.22), "P", font=f, fill="white", anchor="mm")


def m_drift(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.45, cy - S * 0.35, cx + S * 0.45, cy + S * 0.45), fill="#495057")
    d.ellipse((cx - S * 0.25, cy - S * 0.15, cx + S * 0.25, cy + S * 0.25), fill=BG)
    for i in range(6):
        a = 0.6 + i * 0.25
        x, y = cx + math.cos(a) * S * 0.35, cy + S * 0.05 + math.sin(a) * S * 0.33
        d.ellipse((x - S * 0.04, y - S * 0.04, x + S * 0.04, y + S * 0.04), fill=(220, 220, 220, 140))
    _car(d, cx - S * 0.2, cy + S * 0.3, S * 0.2, S * 0.32, ACCENT)


def _terrain(d, cx, cy, S, col, amp=0.08):
    pts = [(cx - S * 0.5, cy + S * 0.5)]
    for i in range(21):
        x = cx - S * 0.5 + i * S * 0.05
        pts.append((x, cy + S * 0.18 - math.sin(i * 0.45) * S * amp - i * S * 0.008))
    pts.append((cx + S * 0.5, cy + S * 0.5))
    d.polygon(pts, fill=col)


def m_hill(d, cx, cy, S, rnd):
    _terrain(d, cx, cy, S, "#6A994E")
    x, y = cx - S * 0.05, cy - S * 0.02
    rr(d, (x - S * 0.2, y - S * 0.14, x + S * 0.2, y + S * 0.02), 12, ACCENT)
    rr(d, (x - S * 0.06, y - S * 0.26, x + S * 0.12, y - S * 0.13), 8, "#BDE0FE")
    for wx in (x - S * 0.13, x + S * 0.13):
        d.ellipse((wx - S * 0.08, y - S * 0.02, wx + S * 0.08, y + S * 0.14), fill="#212529")
        d.ellipse((wx - S * 0.03, y + S * 0.03, wx + S * 0.03, y + S * 0.09), fill="#ADB5BD")
    d.rectangle((cx + S * 0.3, cy - S * 0.3, cx + S * 0.42, cy - S * 0.14), fill="#E63946")


def m_bike(d, cx, cy, S, rnd):
    _terrain(d, cx, cy + S * 0.12, S, "#BC6C25", 0.12)
    x, y = cx, cy - S * 0.08
    for wx in (x - S * 0.17, x + S * 0.17):
        d.ellipse((wx - S * 0.1, y - S * 0.1, wx + S * 0.1, y + S * 0.1), outline="#212529", width=max(4, int(S * 0.03)))
    d.polygon([(x - S * 0.17, y), (x - S * 0.02, y - S * 0.12), (x + S * 0.17, y), (x + S * 0.05, y - S * 0.02)], fill=ACCENT)
    d.ellipse((x - S * 0.06, y - S * 0.34, x + S * 0.06, y - S * 0.22), fill="white")
    d.line((x, y - S * 0.22, x - S * 0.03, y - S * 0.1), fill="#212529", width=max(4, int(S * 0.03)))


def m_truck(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.45, cy + S * 0.18, cx + S * 0.45, cy + S * 0.3), fill="#495057")
    d.rectangle((cx - S * 0.42, cy - S * 0.2, cx + S * 0.12, cy + S * 0.12), fill="#E9ECEF")
    rr(d, (cx + S * 0.12, cy - S * 0.1, cx + S * 0.38, cy + S * 0.12), 10, ACCENT)
    d.rectangle((cx + S * 0.2, cy - S * 0.06, cx + S * 0.34, cy + S * 0.02), fill="#BDE0FE")
    for wx in (-0.32, -0.12, 0.26):
        d.ellipse((cx + S * wx - S * 0.07, cy + S * 0.07, cx + S * wx + S * 0.07, cy + S * 0.21), fill="#212529")


def m_escape(d, cx, cy, S, rnd):
    _road(d, cx, cy, S, 3, "#343A40")
    _car(d, cx, cy - S * 0.15, S * 0.19, S * 0.33, ACCENT)
    _car(d, cx + S * 0.05, cy + S * 0.3, S * 0.19, S * 0.33, "#F8F9FA")
    d.rectangle((cx - S * 0.04, cy + S * 0.17, cx + S * 0.05, cy + S * 0.21), fill="#E63946")
    d.rectangle((cx + S * 0.05, cy + S * 0.17, cx + S * 0.14, cy + S * 0.21), fill="#1D4ED8")


def m_kart(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.45, cy - S * 0.45, cx + S * 0.45, cy + S * 0.45), fill="#2A9D8F")
    d.rounded_rectangle((cx - S * 0.38, cy - S * 0.38, cx + S * 0.38, cy + S * 0.38), radius=int(S * 0.2), outline="#495057", width=int(S * 0.16))
    for i, col in enumerate((PALETTE[0], PALETTE[3], ACCENT)):
        x, y = cx - S * 0.2 + i * S * 0.2, cy + S * 0.32 - i * S * 0.03
        rr(d, (x - S * 0.06, y - S * 0.05, x + S * 0.06, y + S * 0.05), 6, col)
    for k in range(8):
        x = cx - S * 0.45 + k * S * 0.1125
        d.rectangle((x, cy - S * 0.47, x + S * 0.056, cy - S * 0.43), fill="white" if k % 2 else "black")


def m_boat(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.45, cy - S * 0.45, cx + S * 0.45, cy + S * 0.45), fill="#0077B6")
    for k in range(5):
        y = cy - S * 0.35 + k * S * 0.18
        d.arc((cx - S * 0.4, y, cx - S * 0.1, y + S * 0.1), 200, 340, fill="#90E0EF", width=3)
        d.arc((cx + S * 0.1, y + S * 0.05, cx + S * 0.4, y + S * 0.15), 200, 340, fill="#90E0EF", width=3)
    d.polygon([(cx, cy - S * 0.32), (cx + S * 0.12, cy - S * 0.05), (cx + S * 0.1, cy + S * 0.25), (cx - S * 0.1, cy + S * 0.25), (cx - S * 0.12, cy - S * 0.05)], fill=ACCENT)
    d.polygon([(cx - S * 0.12, cy + S * 0.25), (cx, cy + S * 0.42), (cx + S * 0.12, cy + S * 0.25)], fill=(255, 255, 255, 120))
    for sx in (-1, 1):
        d.ellipse((cx + sx * S * 0.3 - S * 0.05, cy - S * 0.2, cx + sx * S * 0.3 + S * 0.05, cy - S * 0.1), fill="#FB8500")


def m_monster(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.45, cy + S * 0.28, cx + S * 0.45, cy + S * 0.4), fill="#7F5539")
    rr(d, (cx + S * 0.08, cy + S * 0.2, cx + S * 0.42, cy + S * 0.28), 6, "#ADB5BD")
    rr(d, (cx - S * 0.28, cy - S * 0.2, cx + S * 0.28, cy), 12, ACCENT)
    rr(d, (cx - S * 0.12, cy - S * 0.32, cx + S * 0.14, cy - S * 0.18), 8, "#BDE0FE")
    for wx in (cx - S * 0.2, cx + S * 0.2):
        d.ellipse((wx - S * 0.15, cy - S * 0.02, wx + S * 0.15, cy + S * 0.28), fill="#212529")
        d.ellipse((wx - S * 0.06, cy + S * 0.07, wx + S * 0.06, cy + S * 0.19), fill="#ADB5BD")


def m_supermarket(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.42, cy - S * 0.3, cx + S * 0.42, cy + S * 0.35), fill="#F8F9FA")
    for r in range(3):
        y = cy - S * 0.22 + r * S * 0.18
        d.rectangle((cx - S * 0.38, y + S * 0.1, cx + S * 0.38, y + S * 0.12), fill="#ADB5BD")
        for k in range(6):
            x = cx - S * 0.35 + k * S * 0.12
            d.rectangle((x, y, x + S * 0.08, y + S * 0.1), fill=PALETTE[(r * 6 + k) % len(PALETTE)])
    d.line((cx + S * 0.05, cy + S * 0.32, cx + S * 0.38, cy + S * 0.32), fill=ACCENT, width=max(4, int(S * 0.025)))
    d.ellipse((cx + S * 0.1, cy + S * 0.36, cx + S * 0.16, cy + S * 0.42), fill="#212529")
    d.ellipse((cx + S * 0.3, cy + S * 0.36, cx + S * 0.36, cy + S * 0.42), fill="#212529")


def m_coffee(d, cx, cy, S, rnd):
    d.rounded_rectangle((cx - S * 0.25, cy - S * 0.1, cx + S * 0.2, cy + S * 0.35), radius=int(S * 0.08), fill="white")
    d.ellipse((cx + S * 0.12, cy, cx + S * 0.36, cy + S * 0.22), outline="white", width=max(6, int(S * 0.04)))
    d.ellipse((cx - S * 0.22, cy - S * 0.14, cx + S * 0.17, cy - S * 0.04), fill="#6F4E37")
    d.ellipse((cx - S * 0.1, cy - S * 0.12, cx + S * 0.05, cy - S * 0.06), fill=ACCENT)
    for i in range(3):
        x = cx - S * 0.12 + i * S * 0.1
        d.arc((x - S * 0.05, cy - S * 0.42, x + S * 0.05, cy - S * 0.18), 100, 260, fill="white", width=max(3, int(S * 0.015)))


def m_carwash(d, cx, cy, S, rnd):
    _car(d, cx, cy + S * 0.1, S * 0.3, S * 0.5, ACCENT)
    for i in range(14):
        x, y = rnd.uniform(cx - S * 0.4, cx + S * 0.4), rnd.uniform(cy - S * 0.4, cy + S * 0.2)
        r = rnd.uniform(S * 0.03, S * 0.07)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 190), outline="#90E0EF")


def m_gas(d, cx, cy, S, rnd):
    d.rounded_rectangle((cx - S * 0.2, cy - S * 0.35, cx + S * 0.12, cy + S * 0.35), radius=int(S * 0.05), fill=ACCENT)
    d.rectangle((cx - S * 0.14, cy - S * 0.28, cx + S * 0.06, cy - S * 0.1), fill="#F8F9FA")
    d.line((cx + S * 0.12, cy - S * 0.15, cx + S * 0.3, cy - S * 0.05, cx + S * 0.3, cy + S * 0.2), fill="#212529", width=max(5, int(S * 0.03)))
    d.rectangle((cx + S * 0.26, cy + S * 0.18, cx + S * 0.36, cy + S * 0.28), fill="#212529")


def m_pet(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.18, cy - S * 0.02, cx + S * 0.18, cy + S * 0.3), fill=ACCENT)
    for dx, dy in ((-0.28, -0.12), (-0.1, -0.3), (0.1, -0.3), (0.28, -0.12)):
        x, y = cx + S * dx, cy + S * dy
        d.ellipse((x - S * 0.08, y - S * 0.08, x + S * 0.08, y + S * 0.08), fill=ACCENT)


def m_house(d, cx, cy, S, rnd):
    _house(d, cx, cy + S * 0.35, S * 0.6, S * 0.4, "#F8F9FA", ACCENT)
    d.rectangle((cx - S * 0.06, cy + S * 0.15, cx + S * 0.06, cy + S * 0.35), fill="#6F4E37")
    d.rectangle((cx - S * 0.24, cy + S * 0.05, cx - S * 0.12, cy + S * 0.15), fill="#BDE0FE")
    d.line((cx + S * 0.15, cy - S * 0.05, cx + S * 0.38, cy - S * 0.38), fill="#ADB5BD", width=max(6, int(S * 0.04)))
    d.rectangle((cx + S * 0.3, cy - S * 0.44, cx + S * 0.44, cy - S * 0.34), fill="#6C757D")


def m_fishing(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.45, cy - S * 0.05, cx + S * 0.45, cy + S * 0.45), fill="#0077B6")
    d.polygon([(cx - S * 0.3, cy - S * 0.12), (cx + S * 0.1, cy - S * 0.12), (cx + S * 0.02, cy - S * 0.02), (cx - S * 0.24, cy - S * 0.02)], fill="#E76F51")
    d.line((cx + S * 0.05, cy - S * 0.15, cx + S * 0.3, cy - S * 0.42), fill="#6F4E37", width=max(4, int(S * 0.02)))
    d.line((cx + S * 0.3, cy - S * 0.42, cx + S * 0.22, cy + S * 0.22), fill="white", width=2)
    x, y = cx + S * 0.12, cy + S * 0.28
    d.ellipse((x - S * 0.14, y - S * 0.07, x + S * 0.14, y + S * 0.07), fill=ACCENT)
    d.polygon([(x - S * 0.12, y), (x - S * 0.24, y - S * 0.07), (x - S * 0.24, y + S * 0.07)], fill=ACCENT)


def m_delivery(d, cx, cy, S, rnd):
    _road(d, cx, cy, S, 3, "#4A4E69")
    _car(d, cx, cy + S * 0.15, S * 0.2, S * 0.34, ACCENT)
    d.rectangle((cx - S * 0.12, cy - S * 0.38, cx + S * 0.12, cy - S * 0.16), fill="#B08968")
    d.line((cx, cy - S * 0.38, cx, cy - S * 0.16), fill="#7F5539", width=max(3, int(S * 0.015)))


def m_construction(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.35, cy - S * 0.42, cx - S * 0.3, cy + S * 0.38), fill=ACCENT)
    d.rectangle((cx - S * 0.4, cy - S * 0.42, cx + S * 0.4, cy - S * 0.37), fill=ACCENT)
    d.line((cx + S * 0.25, cy - S * 0.37, cx + S * 0.25, cy - S * 0.1), fill="#212529", width=2)
    d.rectangle((cx + S * 0.18, cy - S * 0.1, cx + S * 0.32, cy - S * 0.02), fill="#ADB5BD")
    for r in range(4):
        y = cy + S * 0.38 - (r + 1) * S * 0.13
        d.rectangle((cx - S * 0.15, y, cx + S * 0.35, y + S * 0.11), fill="#8D99AE" if r % 2 else "#ADB5BD")


def m_life(d, cx, cy, S, rnd):
    _house(d, cx, cy + S * 0.38, S * 0.7, S * 0.3, "#F8F9FA", ACCENT)
    for i, (dx, h) in enumerate(((-0.18, 0.3), (0.0, 0.22), (0.16, 0.26))):
        x = cx + S * dx
        top = cy - S * 0.05 - S * h
        d.ellipse((x - S * 0.06, top - S * 0.12, x + S * 0.06, top), fill="#FFD6A5")
        d.rectangle((x - S * 0.06, top, x + S * 0.06, cy - S * 0.05), fill=PALETTE[i + 1])
    d.polygon([(cx, cy - S * 0.47), (cx - S * 0.05, cy - S * 0.42), (cx, cy - S * 0.36), (cx + S * 0.05, cy - S * 0.42)], fill="#EF476F")


def _letter(d, x, y, s, ch, col=None):
    tile(d, x, y, s, col or ACCENT)
    f = font(int(s * 0.62))
    tw = d.textlength(ch, font=f)
    d.text((x + (s - tw) / 2, y + s * 0.12), ch, font=f, fill="#1B1B1B")


def m_wordwheel(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.45, cy - S * 0.45, cx + S * 0.45, cy + S * 0.45), fill=(255, 255, 255, 60))
    for i, ch in enumerate("WORDS"):
        a = 2 * math.pi * i / 5 - math.pi / 2
        s = S * 0.24
        _letter(d, cx + math.cos(a) * S * 0.3 - s / 2, cy + math.sin(a) * S * 0.3 - s / 2, s, ch)


def m_wordsearch(d, cx, cy, S, rnd):
    n, s = 4, S * 0.22
    for r in range(n):
        for c in range(n):
            _letter(d, cx - n * s / 2 + c * s, cy - n * s / 2 + r * s, s * 0.92, "FINDWORDABCDXYZE"[r * n + c], "#F8F9FA")
    d.line((cx - n * s / 2 + s * 0.45, cy - n * s / 2 + s * 0.45, cx + n * s / 2 - s * 0.55, cy + n * s / 2 - s * 0.55), fill=ACCENT, width=max(8, int(S * 0.08)))


def m_crossword(d, cx, cy, S, rnd):
    s = S * 0.2
    cells = [(0, 1), (1, 1), (2, 1), (3, 1), (1, 0), (1, 2), (1, 3), (3, 0), (3, 2)]
    for i, (c, r) in enumerate(cells):
        _letter(d, cx - 2 * s + c * s, cy - 2 * s + r * s, s * 0.94, "CROSSWORD"[i], "#F8F9FA" if i % 3 else ACCENT)


def m_trivia(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.4, cy - S * 0.4, cx + S * 0.4, cy + S * 0.4), fill=ACCENT)
    f = font(int(S * 0.6))
    tw = d.textlength("?", font=f)
    d.text((cx - tw / 2, cy - S * 0.36), "?", font=f, fill="#FFFFFF")


def m_symbol(d, cx, cy, S, rnd):
    for i, (dx, dy) in enumerate(((-0.22, -0.22), (0.22, -0.22), (-0.22, 0.22), (0.22, 0.22))):
        x, y = cx + S * dx, cy + S * dy
        rr(d, (x - S * 0.18, y - S * 0.18, x + S * 0.18, y + S * 0.18), int(S * 0.05), PALETTE[i % len(PALETTE)])
    d.ellipse((cx - S * 0.3, cy - S * 0.3, cx - S * 0.14, cy - S * 0.14), fill="white")
    d.polygon([(cx + S * 0.22, cy - S * 0.34), (cx + S * 0.34, cy - S * 0.12), (cx + S * 0.1, cy - S * 0.12)], fill="white")
    d.rectangle((cx - S * 0.3, cy + S * 0.14, cx - S * 0.14, cy + S * 0.3), fill="white")
    d.line((cx + S * 0.12, cy + S * 0.22, cx + S * 0.32, cy + S * 0.22), fill="white", width=max(6, int(S * 0.05)))


def m_globe(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.4, cy - S * 0.4, cx + S * 0.4, cy + S * 0.4), fill="#48CAE4")
    for poly in ([(-0.2, -0.3), (0.05, -0.32), (0.1, -0.1), (-0.12, 0.02), (-0.25, -0.1)],
                 [(0.05, 0.05), (0.28, 0.0), (0.3, 0.2), (0.1, 0.32), (0.0, 0.2)]):
        d.polygon([(cx + S * x, cy + S * y) for x, y in poly], fill="#52B788")
    d.rectangle((cx + S * 0.2, cy - S * 0.45, cx + S * 0.23, cy - S * 0.1), fill="#495057")
    d.rectangle((cx + S * 0.23, cy - S * 0.45, cx + S * 0.43, cy - S * 0.32), fill=ACCENT)


def m_battle(d, cx, cy, S, rnd):
    s = S * 0.22
    for i, ch in enumerate("VS"):
        _letter(d, cx - s * 1.05 + i * s * 1.1, cy - s / 2, s, ch, ACCENT if i else "#F8F9FA")
    d.line((cx - S * 0.4, cy + S * 0.4, cx + S * 0.4, cy - S * 0.4), fill="#ADB5BD", width=max(6, int(S * 0.04)))
    d.line((cx - S * 0.4, cy - S * 0.4, cx + S * 0.4, cy + S * 0.4), fill="#ADB5BD", width=max(6, int(S * 0.04)))


def m_hangman(d, cx, cy, S, rnd):
    w = max(6, int(S * 0.04))
    d.line((cx - S * 0.35, cy + S * 0.4, cx + S * 0.1, cy + S * 0.4), fill="#F8F9FA", width=w)
    d.line((cx - S * 0.2, cy + S * 0.4, cx - S * 0.2, cy - S * 0.4, cx + S * 0.15, cy - S * 0.4, cx + S * 0.15, cy - S * 0.28), fill="#F8F9FA", width=w)
    d.ellipse((cx + S * 0.07, cy - S * 0.28, cx + S * 0.23, cy - S * 0.12), outline=ACCENT, width=w)
    for i in range(3):
        x = cx - S * 0.1 + i * S * 0.17
        d.line((x, cy + S * 0.28, x + S * 0.12, cy + S * 0.28), fill=ACCENT, width=w)


def m_brain(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.38, cy - S * 0.3, cx + S * 0.02, cy + S * 0.28), fill="#FFAFCC")
    d.ellipse((cx - S * 0.02, cy - S * 0.3, cx + S * 0.38, cy + S * 0.28), fill="#FFC8DD")
    for i in range(4):
        y = cy - S * 0.18 + i * S * 0.12
        d.arc((cx - S * 0.3, y - S * 0.06, cx + S * 0.3, y + S * 0.06), 0, 180, fill="#C9184A", width=max(3, int(S * 0.015)))
    d.ellipse((cx + S * 0.2, cy + S * 0.18, cx + S * 0.44, cy + S * 0.42), fill=ACCENT)


def m_picture(d, cx, cy, S, rnd):
    rr(d, (cx - S * 0.42, cy - S * 0.42, cx + S * 0.42, cy + S * 0.12), int(S * 0.05), "#F8F9FA")
    d.polygon([(cx - S * 0.36, cy + S * 0.08), (cx - S * 0.1, cy - S * 0.22), (cx + S * 0.1, cy + S * 0.08)], fill="#52B788")
    d.ellipse((cx + S * 0.12, cy - S * 0.34, cx + S * 0.28, cy - S * 0.18), fill=ACCENT)
    s = S * 0.18
    for i, ch in enumerate("ABC"):
        _letter(d, cx - s * 1.6 + i * s * 1.1, cy + S * 0.2, s, ch)


def _blob(d, cx, cy, r, col):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)


def m_kids_learn(d, cx, cy, S, rnd):
    for i, col in enumerate(PALETTE[:4]):
        x, y = cx + (i % 2 - .5) * S * .42, cy + (i // 2 - .5) * S * .42
        if i == 0:
            _blob(d, x, y, S * .17, col)
        elif i == 1:
            d.rectangle((x - S * .16, y - S * .16, x + S * .16, y + S * .16), fill=col)
        elif i == 2:
            d.polygon([(x, y - S * .18), (x + S * .18, y + S * .15), (x - S * .18, y + S * .15)], fill=col)
        else:
            _star(d, x, y, S * .19, col)


def _star(d, x, y, r, col):
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr_ = r if k % 2 == 0 else r * .45
        pts.append((x + rr_ * math.cos(a), y + rr_ * math.sin(a)))
    d.polygon(pts, fill=col)


def m_kids_piano(d, cx, cy, S, rnd):
    w = S * .12
    for i in range(7):
        x = cx - 3.5 * w + i * w
        d.rectangle((x, cy - S * .3, x + w - 4, cy + S * .3), fill="#FFFFFF", outline="#333333", width=3)
    for i in (0, 1, 3, 4, 5):
        x = cx - 3.5 * w + (i + 1) * w - w * .3
        d.rectangle((x, cy - S * .3, x + w * .6, cy + S * .05), fill="#222222")
    for i in range(3):
        _blob(d, cx - S * .25 + i * S * .25, cy - S * .42, S * .05, PALETTE[i])


def m_kids_animals(d, cx, cy, S, rnd):
    _blob(d, cx, cy + S * .05, S * .3, "#FFFFFF")
    for dx, col in ((-.2, "#333333"), (.2, "#333333")):
        _blob(d, cx + S * dx, cy - S * .22, S * .1, col)
    _blob(d, cx - S * .1, cy, S * .05, "#222222")
    _blob(d, cx + S * .1, cy, S * .05, "#222222")
    d.ellipse((cx - S * .14, cy + S * .1, cx + S * .14, cy + S * .26), fill="#F4A6B7")
    for k in range(3):
        d.arc((cx + S * (.3 + k * .05), cy - S * (.2 + k * .06), cx + S * (.42 + k * .07), cy + S * (.0 + k * .06)), -60, 60, fill=ACCENT, width=6)


def m_kids_coloring(d, cx, cy, S, rnd):
    d.rounded_rectangle((cx - S * .4, cy - S * .35, cx + S * .25, cy + S * .4), radius=int(S * .04), fill="#FFFFFF")
    _blob(d, cx - S * .1, cy, S * .14, PALETTE[1])
    d.polygon([(cx + S * .05, cy - S * .5), (cx + S * .42, cy + S * .25), (cx + S * .32, cy + S * .3)], fill=ACCENT)
    d.polygon([(cx + S * .42, cy + S * .25), (cx + S * .32, cy + S * .3), (cx + S * .45, cy + S * .38)], fill="#333333")


def m_kids_math(d, cx, cy, S, rnd):
    f = font(int(S * .34))
    for i, (t, col) in enumerate((("1", PALETTE[0]), ("+", "#FFFFFF"), ("2", PALETTE[1]))):
        x = cx - S * .32 + i * S * .3
        tw = d.textlength(t, font=f)
        d.text((x - tw / 2, cy - S * .25), t, font=f, fill=col)
    for i in range(3):
        _blob(d, cx - S * .2 + i * S * .2, cy + S * .3, S * .07, ACCENT)


def m_kids_shapes(d, cx, cy, S, rnd):
    d.polygon([(cx - S * .25, cy - S * .3), (cx - S * .05, cy + S * .05), (cx - S * .45, cy + S * .05)], fill=PALETTE[2])
    _blob(d, cx + S * .22, cy - S * .15, S * .15, PALETTE[3])
    d.rectangle((cx - S * .35, cy + S * .15, cx - S * .05, cy + S * .42), fill=PALETTE[1])
    _star(d, cx + S * .22, cy + S * .28, S * .17, PALETTE[0])


def m_kids_memory(d, cx, cy, S, rnd):
    for i in range(4):
        x, y = cx + (i % 2 - .5) * S * .42, cy + (i // 2 - .5) * S * .5
        rr(d, (x - S * .17, y - S * .22, x + S * .17, y + S * .22), int(S * .04), "#FFFFFF" if i in (0, 3) else ACCENT)
        if i in (0, 3):
            _star(d, x, y, S * .1, PALETTE[0])


def m_kids_abc(d, cx, cy, S, rnd):
    s = S * .26
    for i, ch in enumerate("ABC"):
        _letter(d, cx - s * 1.6 + i * s * 1.1, cy - s / 2, s, ch, PALETTE[i])


def m_kids_puzzle(d, cx, cy, S, rnd):
    for i in range(4):
        x, y = cx + (i % 2 - .5) * S * .4 + (6 if i == 3 else 0), cy + (i // 2 - .5) * S * .4 + (8 if i == 3 else 0)
        rr(d, (x - S * .19, y - S * .19, x + S * .19, y + S * .19), int(S * .03), PALETTE[i])
        _blob(d, x + S * .19, y, S * .05, PALETTE[i])


def m_kids_mini(d, cx, cy, S, rnd):
    for i in range(5):
        x, y = cx + (i - 2) * S * .18, cy - S * .05 + (i % 2) * S * .12
        d.ellipse((x - S * .09, y - S * .12, x + S * .09, y + S * .12), fill=PALETTE[i])
        d.line((x, y + S * .12, x, y + S * .38), fill="#FFFFFF", width=3)


def _stickman(d, cx, cy, S, col, kick=False):
    w = max(3, int(S * 0.05))
    hip = (cx, cy + S * 0.08)
    neck = (cx + S * 0.03, cy - S * 0.17)
    d.line([hip, neck], fill=col, width=w)
    d.line([hip, (cx - S * 0.12, cy + S * 0.36)], fill=col, width=w)
    d.line([hip, (cx + S * 0.34, cy - S * 0.02) if kick else (cx + S * 0.12, cy + S * 0.36)], fill=col, width=w)
    d.line([(neck[0], neck[1] + S * 0.04), (cx + S * 0.3, cy - S * 0.16)], fill=col, width=w)
    d.line([(neck[0], neck[1] + S * 0.04), (cx - S * 0.16, cy + S * 0.02)], fill=col, width=w)
    r = S * 0.08
    d.ellipse((neck[0] - r, neck[1] - 2.2 * r, neck[0] + r, neck[1] - 0.2 * r), fill=col)
    return neck, r


def m_zombie(d, cx, cy, S, rnd):
    r = S * 0.24
    for sx in (-1, 1):
        d.line([(cx + sx * r * 0.6, cy + r * 0.2), (cx + sx * r * 0.6, cy - r * 1.6)], fill="#74C69D", width=int(S * 0.07))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#74C69D")
    for sx in (-1, 1):
        d.ellipse((cx + sx * r * 0.4 - r * 0.15, cy - r * 0.3 - r * 0.15, cx + sx * r * 0.4 + r * 0.15, cy - r * 0.3 + r * 0.15), fill="#D00000")
    d.rectangle((cx - r * 0.4, cy + r * 0.3, cx + r * 0.4, cy + r * 0.45), fill="#1B4332")


def m_stickman(d, cx, cy, S, rnd):
    _stickman(d, cx - S * 0.12, cy, S * 0.9, "#FFFFFF", kick=True)
    _stickman(d, cx + S * 0.28, cy + S * 0.04, S * 0.7, PALETTE[0])


def m_ninja(d, cx, cy, S, rnd):
    neck, r = _stickman(d, cx, cy, S, "#1B263B")
    d.rectangle((neck[0] - r, neck[1] - 1.4 * r, neck[0] + r, neck[1] - 1.0 * r), fill="#E63946")
    d.line([(neck[0] - r, neck[1] - 1.2 * r), (neck[0] - 2.6 * r, neck[1] - 0.6 * r)], fill="#E63946", width=int(S * 0.03))
    for i in range(3):
        x = cx - S * 0.36 + i * S * 0.08
        d.line([(x, cy + S * 0.4), (x + S * 0.05, cy + S * 0.4)], fill="white", width=4)


def m_dungeon(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.36, cy - S * 0.36, cx + S * 0.36, cy + S * 0.36), fill="#3A3335")
    d.line([(cx - S * 0.2, cy + S * 0.25), (cx + S * 0.22, cy - S * 0.25)], fill="#E0E1DD", width=int(S * 0.06))
    d.line([(cx - S * 0.12, cy + S * 0.08), (cx - S * 0.0, cy + S * 0.2)], fill="#B08968", width=int(S * 0.06))
    d.ellipse((cx + S * 0.05, cy + S * 0.05, cx + S * 0.33, cy + S * 0.3), fill="#52B788")


def m_alien_defense(d, cx, cy, S, rnd):
    d.pieslice((cx - S * 0.36, cy + S * 0.1, cx + S * 0.36, cy + S * 0.6), 180, 360, fill="#9D4EDD")
    d.line([(cx, cy + S * 0.25), (cx + S * 0.1, cy - S * 0.05)], fill="#E0E1DD", width=int(S * 0.06))
    for i, (x, y) in enumerate(((-0.25, -0.3), (0.1, -0.38), (0.3, -0.2))):
        X, Y, r = cx + x * S, cy + y * S, S * 0.08
        d.polygon([(X, Y + r), (X + r, Y - r * 0.5), (X, Y - r), (X - r, Y - r * 0.5)], fill=PALETTE[(i + 4) % 8])


def m_robot(d, cx, cy, S, rnd):
    r = S * 0.26
    d.rounded_rectangle((cx - r, cy - r, cx + r, cy + r), radius=int(r * 0.3), fill="#ADB5BD")
    d.rectangle((cx - r * 0.65, cy - r * 0.45, cx + r * 0.65, cy - r * 0.05), fill="#0D1B2A")
    d.ellipse((cx - r * 0.15, cy - r * 0.38, cx + r * 0.15, cy - r * 0.12), fill="#00F5D4")
    d.line([(cx, cy - r), (cx, cy - r * 1.5)], fill="#ADB5BD", width=int(S * 0.03))
    d.ellipse((cx - r * 0.12, cy - r * 1.7, cx + r * 0.12, cy - r * 1.45), fill="#E63946")


def m_shadow(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.36, cy - S * 0.36, cx + S * 0.36, cy + S * 0.36), fill="#F1FAEE")
    _stickman(d, cx, cy + S * 0.02, S * 0.95, "#0D1B2A", kick=True)


def m_beast(d, cx, cy, S, rnd):
    r = S * 0.3
    d.ellipse((cx - r, cy - r * 0.8, cx + r, cy + r * 0.8), fill="#9D0208")
    for sx in (-1, 1):
        d.polygon([(cx + sx * r * 0.5, cy - r * 0.5), (cx + sx * r * 0.95, cy - r * 1.3), (cx + sx * r * 0.2, cy - r * 0.7)], fill="#F1FAEE")
        d.ellipse((cx + sx * r * 0.35 - r * 0.12, cy - r * 0.2 - r * 0.12, cx + sx * r * 0.35 + r * 0.12, cy - r * 0.2 + r * 0.12), fill="#FFD60A")
    d.line([(cx - S * 0.38, cy + S * 0.38), (cx + S * 0.1, cy - S * 0.1)], fill="#E0E1DD", width=int(S * 0.05))


def m_island(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.4, cy + S * 0.1, cx + S * 0.4, cy + S * 0.4), fill="#F4D58D")
    d.line([(cx, cy + S * 0.25), (cx + S * 0.05, cy - S * 0.2)], fill="#7F5539", width=int(S * 0.05))
    for a in range(5):
        import math as _m
        ang = -_m.pi / 2 + (a - 2) * 0.6
        d.line([(cx + S * 0.05, cy - S * 0.2), (cx + S * 0.05 + _m.cos(ang) * S * 0.25, cy - S * 0.2 + _m.sin(ang) * S * 0.25 + S * 0.05)], fill="#2D6A4F", width=int(S * 0.05))


def m_spaceship(d, cx, cy, S, rnd):
    d.polygon([(cx, cy - S * 0.4), (cx + S * 0.3, cy + S * 0.25), (cx, cy + S * 0.12), (cx - S * 0.3, cy + S * 0.25)], fill=ACCENT)
    d.ellipse((cx - S * 0.07, cy - S * 0.12, cx + S * 0.07, cy + S * 0.02), fill="#90E0EF")
    d.ellipse((cx - S * 0.06, cy + S * 0.2, cx + S * 0.06, cy + S * 0.42), fill="#FFB703")
    for i in range(3):
        d.line([(cx - S * 0.02 + (i - 1) * S * 0.12, cy - S * 0.45 - i * 8), (cx - S * 0.02 + (i - 1) * S * 0.12, cy - S * 0.55 - i * 8)], fill="#FFFF3F", width=5)


def _ball_hex(d, cx, cy, r):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#FFFFFF", outline="#222222", width=max(2, int(r * 0.06)))
    import math as _m
    pts = [(cx + _m.cos(_m.pi / 2 * 3 + k * 2 * _m.pi / 5) * r * 0.35, cy + _m.sin(_m.pi / 2 * 3 + k * 2 * _m.pi / 5) * r * 0.35) for k in range(5)]
    d.polygon(pts, fill="#222222")


def m_football(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.45, cy + S * 0.2, cx + S * 0.45, cy + S * 0.45), fill="#2D6A4F")
    d.line([(cx - S * 0.35, cy - S * 0.1), (cx - S * 0.35, cy - S * 0.4), (cx + S * 0.35, cy - S * 0.4), (cx + S * 0.35, cy - S * 0.1)], fill="#FFFFFF", width=int(S * 0.04))
    _ball_hex(d, cx, cy + S * 0.08, S * 0.2)


def m_basketball(d, cx, cy, S, rnd):
    r = S * 0.3
    d.ellipse((cx - r, cy - r + S * 0.08, cx + r, cy + r + S * 0.08), fill="#F77F00", outline="#3D1E00", width=int(S * 0.025))
    d.line([(cx - r, cy + S * 0.08), (cx + r, cy + S * 0.08)], fill="#3D1E00", width=int(S * 0.025))
    d.line([(cx, cy - r + S * 0.08), (cx, cy + r + S * 0.08)], fill="#3D1E00", width=int(S * 0.025))
    d.line([(cx - S * 0.3, cy - S * 0.32), (cx + S * 0.3, cy - S * 0.32)], fill="#E63946", width=int(S * 0.05))


def m_penalty(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.42, cy - S * 0.35, cx + S * 0.42, cy + S * 0.05), outline="#FFFFFF", width=int(S * 0.04))
    for i in range(1, 6):
        x = cx - S * 0.42 + i * S * 0.14
        d.line([(x, cy - S * 0.35), (x, cy + S * 0.05)], fill="#FFFFFF66", width=2)
    d.ellipse((cx + S * 0.12, cy - S * 0.3, cx + S * 0.3, cy - S * 0.12), fill="#00B4D8")
    _ball_hex(d, cx - S * 0.1, cy + S * 0.28, S * 0.13)


def m_pingpong(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.32, cy - S * 0.38, cx + S * 0.18, cy + S * 0.12), fill="#E63946", outline="#111111", width=int(S * 0.02))
    d.line([(cx + S * 0.08, cy + S * 0.02), (cx + S * 0.3, cy + S * 0.32)], fill="#8D6E63", width=int(S * 0.07))
    d.ellipse((cx + S * 0.18, cy - S * 0.36, cx + S * 0.32, cy - S * 0.22), fill="#FFFFFF")


def m_golf(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.45, cy + S * 0.15, cx + S * 0.45, cy + S * 0.42), fill="#52B788")
    d.ellipse((cx - S * 0.06, cy + S * 0.24, cx + S * 0.06, cy + S * 0.3), fill="#081C15")
    d.line([(cx, cy + S * 0.27), (cx, cy - S * 0.38)], fill="#FFFFFF", width=int(S * 0.025))
    d.polygon([(cx, cy - S * 0.38), (cx + S * 0.25, cy - S * 0.3), (cx, cy - S * 0.22)], fill="#E63946")
    d.ellipse((cx - S * 0.3, cy + S * 0.18, cx - S * 0.18, cy + S * 0.3), fill="#FFFFFF")


def m_bowling(d, cx, cy, S, rnd):
    for i, x in enumerate((-0.18, 0.0, 0.18)):
        px = cx + x * S
        d.ellipse((px - S * 0.06, cy - S * 0.38, px + S * 0.06, cy - S * 0.24), fill="#FFFFFF")
        d.ellipse((px - S * 0.08, cy - S * 0.26, px + S * 0.08, cy + S * 0.02), fill="#FFFFFF")
        d.rectangle((px - S * 0.05, cy - S * 0.26, px + S * 0.05, cy - S * 0.22), fill="#E63946")
    r = S * 0.2
    d.ellipse((cx - r, cy + S * 0.05, cx + r, cy + S * 0.05 + 2 * r), fill="#3A0CA3")
    for ox, oy in ((-0.05, 0.12), (0.04, 0.1), (0.0, 0.18)):
        d.ellipse((cx + ox * S - 5, cy + oy * S - 5, cx + ox * S + 5, cy + oy * S + 5), fill="#000000")


def m_archery(d, cx, cy, S, rnd):
    cols = ["#FFFFFF", "#222222", "#0077B6", "#E63946", "#FFD60A"]
    for i, c in enumerate(cols):
        r = S * 0.4 * (5 - i) / 5
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
    d.line([(cx + S * 0.02, cy - S * 0.02), (cx + S * 0.42, cy - S * 0.42)], fill="#7F5539", width=int(S * 0.03))
    d.polygon([(cx + S * 0.36, cy - S * 0.46), (cx + S * 0.46, cy - S * 0.46), (cx + S * 0.46, cy - S * 0.36)], fill="#E63946")


def m_billiards(d, cx, cy, S, rnd):
    d.rounded_rectangle((cx - S * 0.45, cy - S * 0.3, cx + S * 0.45, cy + S * 0.3), radius=int(S * 0.08), fill="#2E7D32", outline="#5C3A21", width=int(S * 0.05))
    cols = ["#FFD60A", "#1D4ED8", "#E63946", "#111111", "#F77F00", "#7B2CBF"]
    k = 0
    for row in range(3):
        for j in range(row + 1):
            x = cx + S * 0.15 + row * S * 0.09
            y = cy + (j - row / 2) * S * 0.1
            d.ellipse((x - S * 0.05, y - S * 0.05, x + S * 0.05, y + S * 0.05), fill=cols[k % 6])
            k += 1
    d.ellipse((cx - S * 0.28, cy - S * 0.05, cx - S * 0.18, cy + S * 0.05), fill="#FFFFFF")


def m_darts(d, cx, cy, S, rnd):
    import math as _m
    r = S * 0.4
    d.ellipse((cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8), fill="#111111")
    for i in range(20):
        a0 = i * 18 - 99
        d.pieslice((cx - r, cy - r, cx + r, cy + r), a0, a0 + 18, fill="#F1E3C6" if i % 2 else "#1B1B1B")
    d.ellipse((cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62), outline="#D62828", width=int(S * 0.03))
    d.ellipse((cx - r * 0.1, cy - r * 0.1, cx + r * 0.1, cy + r * 0.1), fill="#D62828")
    d.line([(cx + S * 0.03, cy - S * 0.03), (cx + S * 0.3, cy - S * 0.3)], fill="#0077B6", width=int(S * 0.04))


def m_tennis(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.3, cy - S * 0.42, cx + S * 0.12, cy + S * 0.05), outline="#E63946", width=int(S * 0.05))
    for i in range(-2, 3):
        d.line([(cx - S * 0.09 + i * S * 0.06, cy - S * 0.38), (cx - S * 0.09 + i * S * 0.06, cy + S * 0.01)], fill="#FFFFFF", width=2)
    d.line([(cx + S * 0.05, cy + S * 0.02), (cx + S * 0.25, cy + S * 0.35)], fill="#333333", width=int(S * 0.06))
    d.ellipse((cx + S * 0.12, cy - S * 0.15, cx + S * 0.34, cy + S * 0.07), fill="#D9ED92", outline="#FFFFFF", width=3)


def m_antistress(d, cx, cy, S, rnd):
    import math as _m
    for k in range(3):
        a = k * 2 * _m.pi / 3 - _m.pi / 2
        ex, ey = cx + _m.cos(a) * S * 0.25, cy + _m.sin(a) * S * 0.25
        d.line([(cx, cy), (ex, ey)], fill="#6A4C93", width=int(S * 0.14))
        d.ellipse((ex - S * 0.13, ey - S * 0.13, ex + S * 0.13, ey + S * 0.13), fill=["#FFADAD", "#CAFFBF", "#A0C4FF"][k])
    d.ellipse((cx - S * 0.1, cy - S * 0.1, cx + S * 0.1, cy + S * 0.1), fill="#FFD6A5")


def m_popit(d, cx, cy, S, rnd):
    cols = ["#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF", "#BDB2FF"]
    r = S * 0.07
    for j in range(5):
        for i in range(5):
            x = cx + (i - 2) * r * 2.4 + (r * 1.2 if j % 2 else 0) - r * 0.6
            y = cy + (j - 2) * r * 2.2
            if (x - cx) ** 2 + (y - cy) ** 2 > (S * 0.42) ** 2:
                continue
            d.ellipse((x - r, y - r, x + r, y + r), fill=cols[j % 6], outline="#00000022", width=2)


def m_sandart(d, cx, cy, S, rnd):
    import math as _m
    cols = ["#E76F51", "#F4A261", "#E9C46A", "#2A9D8F", "#264653"]
    w, h = S * 0.5, S * 0.7
    x0, y0 = cx - w / 2, cy - h / 2
    for k, c in reversed(list(enumerate(cols))):
        pts = [(x0 + w * i / 10, y0 + h * (1 - (k + 1) / 5) + _m.sin(i * 0.9 + k) * S * 0.03) for i in range(11)]
        d.polygon(pts + [(x0 + w, y0 + h), (x0, y0 + h)], fill=c)
    d.rectangle((x0, y0, x0 + w, y0 + h), outline="#8D6E63", width=int(S * 0.03))


def m_cleaning(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.38, cy - S * 0.38, cx + S * 0.38, cy + S * 0.38), fill="#F8F9FA", outline="#ADB5BD", width=6)
    d.ellipse((cx - S * 0.35, cy - S * 0.1, cx + S * 0.05, cy + S * 0.3), fill="#9C664488")
    d.rounded_rectangle((cx - S * 0.05, cy - S * 0.3, cx + S * 0.33, cy - S * 0.08), radius=int(S * 0.05), fill="#FFD166")
    for k in range(4):
        x, y = cx + S * (0.1 + k * 0.07), cy - S * (0.4 + (k % 2) * 0.05)
        d.ellipse((x - 8, y - 8, x + 8, y + 8), fill="#FFFFFFCC")


def m_zengarden(d, cx, cy, S, rnd):
    d.rectangle((cx - S * 0.42, cy - S * 0.35, cx + S * 0.42, cy + S * 0.35), fill="#F1E3C6")
    for k in range(9):
        y = cy - S * 0.3 + k * S * 0.075
        d.line([(cx - S * 0.4, y), (cx + S * 0.4, y)], fill="#C9B79C", width=3)
    d.ellipse((cx - S * 0.2, cy - S * 0.12, cx + S * 0.05, cy + S * 0.08), fill="#6C757D")
    d.ellipse((cx + S * 0.12, cy + S * 0.05, cx + S * 0.28, cy + S * 0.18), fill="#495057")


def m_mergefruit(d, cx, cy, S, rnd):
    d.ellipse((cx - S * 0.32, cy - S * 0.22, cx + S * 0.32, cy + S * 0.4), fill="#2D6A4F")
    d.ellipse((cx - S * 0.26, cy - S * 0.16, cx + S * 0.26, cy + S * 0.34), fill="#80ED99")
    d.ellipse((cx - S * 0.2, cy - S * 0.42, cx - S * 0.02, cy - S * 0.24), fill="#D00000")
    d.ellipse((cx + S * 0.04, cy - S * 0.46, cx + S * 0.26, cy - S * 0.24), fill="#FFB703")
    for ox in (-0.08, 0.08):
        d.ellipse((cx + ox * S - 6, cy + S * 0.05 - 6, cx + ox * S + 6, cy + S * 0.05 + 6), fill="#222222")


def m_screw(d, cx, cy, S, rnd):
    d.rounded_rectangle((cx - S * 0.4, cy - S * 0.2, cx + S * 0.3, cy + S * 0.15), radius=int(S * 0.06), fill="#457B9DCC")
    d.rounded_rectangle((cx - S * 0.25, cy - S * 0.05, cx + S * 0.42, cy + S * 0.3), radius=int(S * 0.06), fill="#E63946CC")
    for x, y, c in ((-0.3, -0.1, "#FFB703"), (0.2, -0.1, "#2A9D8F"), (0.32, 0.2, "#9D4EDD")):
        px, py = cx + x * S, cy + y * S
        d.ellipse((px - S * 0.06, py - S * 0.06, px + S * 0.06, py + S * 0.06), fill=c, outline="#343A40", width=4)
        d.line([(px - S * 0.03, py - S * 0.03), (px + S * 0.03, py + S * 0.03)], fill="#000000", width=3)


def m_goodssort(d, cx, cy, S, rnd):
    cols = ["#E63946", "#FFB703", "#2A9D8F"]
    for row in range(2):
        y = cy - S * 0.2 + row * S * 0.32
        d.rectangle((cx - S * 0.42, y + S * 0.12, cx + S * 0.42, y + S * 0.16), fill="#7F5539")
        for k in range(3):
            x = cx + (k - 1) * S * 0.26
            c = cols[0] if row == 0 else cols[k]
            d.rounded_rectangle((x - S * 0.08, y - S * 0.08, x + S * 0.08, y + S * 0.12), radius=8, fill=c)


def m_tilematch(d, cx, cy, S, rnd):
    cols = ["#FF8FAB", "#80ED99", "#FFD60A"]
    for k, (ox, oy) in enumerate(((-0.18, -0.12), (0.06, -0.2), (-0.04, 0.08))):
        x, y = cx + ox * S, cy + oy * S
        d.rounded_rectangle((x - S * 0.14, y - S * 0.16, x + S * 0.14, y + S * 0.16), radius=12, fill="#FFFCF2", outline="#2D6A4F", width=5)
        d.ellipse((x - S * 0.07, y - S * 0.07, x + S * 0.07, y + S * 0.07), fill=cols[k])


def m_hexasort(d, cx, cy, S, rnd):
    import math as _m
    cols = ["#E63946", "#FFB703", "#2A9D8F", "#9D4EDD"]
    for k in range(4):
        y = cy + S * 0.15 - k * S * 0.08
        pts = [(cx + _m.cos(a * _m.pi / 3) * S * 0.3, y + _m.sin(a * _m.pi / 3) * S * 0.2) for a in range(6)]
        d.polygon(pts, fill=cols[k], outline="#00000055")


def m_cards(d, cx, cy, S, rnd):
    # Yelpaze gibi açılmış üç kart: stüdyonun kendi kart tasarımı.
    import math
    w, h = S * 0.36, S * 0.5
    cols = ["#1E2430", "#CF3B35", "#1E2430"]
    for k, ang in enumerate((-18, 0, 18)):
        a = math.radians(ang)
        ox, oy = cx + math.sin(a) * S * 0.22, cy - math.cos(a) * S * 0.02 + abs(ang) * S * 0.003
        pts = []
        for (px, py) in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
            pts.append((ox + px * math.cos(a) - py * math.sin(a), oy + px * math.sin(a) + py * math.cos(a)))
        d.polygon(pts, fill="#FBF7EE", outline="#D9D1C0")
        r = S * 0.07
        d.ellipse([ox - r, oy - r, ox + r, oy + r], fill=cols[k])


def m_board(d, cx, cy, S, rnd):
    # Eğik duran 4x4 ahşap tahta, üstünde iki taş ve bir zar: stüdyonun kendi çizimi.
    n, s = 4, S * 0.17
    x0, y0 = cx - n * s / 2, cy - n * s / 2 - S * 0.04
    rr(d, (x0 - s * 0.25, y0 - s * 0.25, x0 + n * s + s * 0.25, y0 + n * s + s * 0.25), s * 0.3, "#8A5A34")
    for gy in range(n):
        for gx in range(n):
            c = "#F1DDB8" if (gx + gy) % 2 == 0 else "#B9824F"
            d.rectangle((x0 + gx * s, y0 + gy * s, x0 + (gx + 1) * s, y0 + (gy + 1) * s), fill=c)
    for (gx, gy, c, o) in ((1, 2, "#24303F", "#0F151D"), (2, 1, "#F7F2E8", "#C9BFAE")):
        px, py, r = x0 + (gx + 0.5) * s, y0 + (gy + 0.5) * s, s * 0.38
        d.ellipse((px - r, py - r + s * 0.06, px + r, py + r + s * 0.06), fill=o)
        d.ellipse((px - r, py - r, px + r, py + r), fill=c)
    dx, dy, ds = cx + S * 0.26, cy + S * 0.24, S * 0.2
    rr(d, (dx - ds / 2, dy - ds / 2, dx + ds / 2, dy + ds / 2), ds * 0.2, "#FFFFFF", outline="#D8D0C2", width=2)
    pr = ds * 0.09
    for (ox, oy) in ((-0.25, -0.25), (0, 0), (0.25, 0.25)):
        d.ellipse((dx + ox * ds - pr, dy + oy * ds - pr, dx + ox * ds + pr, dy + oy * ds + pr), fill="#C0392B")


MOTIFS = {
    "board": m_board,
    "cards": m_cards,
    "blocks": m_blocks, "bottles": m_bottles, "balls": m_balls, "2048": m_2048,
    "sudoku": m_sudoku, "jigsaw": m_jigsaw, "nonogram": m_nonogram,
    "unblock": m_unblock, "numbers": m_numbers, "dots": m_dots,
    "verse": m_verse, "snake": m_snake, "bricks": m_bricks, "bubbles": m_bubbles,
    "invaders": m_invaders, "maze": m_maze, "flappy": m_flappy, "bounce": m_bounce,
    "stack": m_stack, "crossy": m_crossy,
    "td": m_td, "civ": m_civ, "empire": m_empire, "factory": m_factory, "city": m_city,
    "farm": m_farm, "restaurant": m_restaurant, "airport": m_airport, "hotel": m_hotel, "colony": m_colony,
    "traffic": m_traffic, "parking": m_parking, "drift": m_drift, "hill": m_hill, "bike": m_bike,
    "truck": m_truck, "escape": m_escape, "kart": m_kart, "boat": m_boat, "monster": m_monster,
    "supermarket": m_supermarket, "coffee": m_coffee, "carwash": m_carwash, "gas": m_gas, "pet": m_pet,
    "house": m_house, "fishing": m_fishing, "delivery": m_delivery, "construction": m_construction, "life": m_life,
    "wordwheel": m_wordwheel, "wordsearch": m_wordsearch, "crossword": m_crossword, "trivia": m_trivia,
    "symbol": m_symbol, "globe": m_globe, "battle": m_battle, "hangman": m_hangman, "brain": m_brain, "picture": m_picture,
    "kids_learn": m_kids_learn, "kids_piano": m_kids_piano, "kids_animals": m_kids_animals, "kids_coloring": m_kids_coloring,
    "kids_math": m_kids_math, "kids_shapes": m_kids_shapes, "kids_memory": m_kids_memory, "kids_abc": m_kids_abc,
    "kids_puzzle": m_kids_puzzle, "kids_mini": m_kids_mini,
    "zombie": m_zombie, "stickman": m_stickman, "ninja": m_ninja, "dungeon": m_dungeon, "alien_defense": m_alien_defense,
    "robot": m_robot, "shadow": m_shadow, "beast": m_beast, "island": m_island, "spaceship": m_spaceship,
    "football": m_football, "basketball": m_basketball, "penalty": m_penalty, "pingpong": m_pingpong, "golf": m_golf,
    "bowling": m_bowling, "archery": m_archery, "billiards": m_billiards, "darts": m_darts, "tennis": m_tennis,
    "antistress": m_antistress, "popit": m_popit, "sandart": m_sandart, "cleaning": m_cleaning, "zengarden": m_zengarden,
    "mergefruit": m_mergefruit, "screw": m_screw, "goodssort": m_goodssort, "tilematch": m_tilematch, "hexasort": m_hexasort,
}


def lighter(h, k=40):
    return "#%02X%02X%02X" % tuple(min(255, c + k) for c in hex2rgb(h))


def draw_motif(img, cx, cy, S, seed=7):
    d = ImageDraw.Draw(img, "RGBA")
    MOTIFS.get(MOTIF, m_blocks)(d, cx, cy, S, random.Random(seed))


def icon(size=1024):
    img = gradient(size, size, lighter(BG, 35), BG).convert("RGBA")
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((size * .15, size * .15, size * .85, size * .85), fill=hex2rgb(ACCENT) + (90,))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(size // 10)))
    draw_motif(img, size / 2, size / 2, size * 0.62)
    return img


def foreground(size=1024):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_motif(img, size / 2, size / 2, size * 0.5)
    return img


def fit(d, text, size, max_w, bold=True):
    f = font(size, bold)
    while size > 14 and d.textbbox((0, 0), text, font=f)[2] > max_w:
        size -= 2
        f = font(size, bold)
    return f


def text_center(d, y, text, f, w, fill="white"):
    tw = d.textbbox((0, 0), text, font=f)[2]
    d.text(((w - tw) / 2, y), text, font=f, fill=fill)


def feature_graphic(lang):
    w, h = 1024, 500
    img = gradient(w, h, lighter(BG, 30), BG).convert("RGBA")
    draw_motif(img, 250, 250, 360)
    d = ImageDraw.Draw(img)
    f1 = fit(d, TITLE[lang], 56, 520)
    f2 = fit(d, TAGLINE[lang], 30, 520, False)
    d.text((470, 160), TITLE[lang], font=f1, fill="white")
    d.text((470, 250), TAGLINE[lang], font=f2, fill="#FFFFFFDD")
    return img.convert("RGB")


def screenshot(lang, idx):
    w, h = 1080, 1920
    img = gradient(w, h, lighter(BG, 30), BG).convert("RGBA")
    d = ImageDraw.Draw(img)
    text_center(d, 120, FEATURES[lang][idx], fit(d, FEATURES[lang][idx], 64, 980), w)
    # phone frame with game art
    rr(d, (140, 330, 940, 1800), 70, "#111111")
    inner = gradient(740, 1400, lighter(BG, 15), BG)
    img.paste(inner, (170, 360))
    draw_motif(img, 540, 1000, 640, seed=idx + 3)
    d = ImageDraw.Draw(img)
    text_center(d, 420, TITLE[lang], fit(d, TITLE[lang], 48, 680), w)
    return img.convert("RGB")


# ---------------------------------------------------------------- audio
RATE = 22050


def tone(freqs, dur, vol=0.4, decay=6.0, kind="sine"):
    n = int(RATE * dur)
    out = []
    for i in range(n):
        t = i / RATE
        env = math.exp(-decay * t) * min(1.0, i / 200)
        v = 0.0
        for f in freqs:
            ph = 2 * math.pi * f * t
            v += math.sin(ph) if kind == "sine" else (1 if math.sin(ph) > 0 else -1) * 0.5
        out.append(vol * env * v / max(1, len(freqs)))
    return out


def seq(parts):
    out = []
    for p in parts:
        out += p
    return out


def save_wav(path, samples):
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32000)) for s in samples))


def sweep(f0, f1, dur, vol=0.4, vib=0.0, vibf=6.0, harm=(1.0,), noise=0.0, att=0.02, rel=0.08, seed=1):
    rnd = random.Random(seed)
    n = int(RATE * dur)
    out, ph = [], 0.0
    for i in range(n):
        t = i / RATE
        k = t / dur
        f = f0 + (f1 - f0) * k
        f *= 1 + vib * math.sin(2 * math.pi * vibf * t)
        ph += 2 * math.pi * f / RATE
        v = sum(a * math.sin(ph * (j + 1)) for j, a in enumerate(harm)) / sum(harm)
        if noise:
            v = v * (1 - noise) + noise * (rnd.random() * 2 - 1)
        env = min(1.0, t / att) * min(1.0, (dur - t) / rel)
        out.append(vol * env * v)
    return out


def silence(dur):
    return [0.0] * int(RATE * dur)


NOTES = [("c4", 261.63), ("d4", 293.66), ("e4", 329.63), ("f4", 349.23), ("g4", 392.0), ("a4", 440.0), ("b4", 493.88),
         ("c5", 523.25), ("d5", 587.33), ("e5", 659.25), ("f5", 698.46), ("g5", 783.99), ("a5", 880.0), ("b5", 987.77), ("c6", 1046.5)]


def kid_sounds(out):
    for name, f in NOTES:
        n = int(RATE * 1.1)
        smp = []
        for i in range(n):
            t = i / RATE
            v = (math.sin(2 * math.pi * f * t) + 0.45 * math.sin(4 * math.pi * f * t) * math.exp(-3 * t)
                 + 0.2 * math.sin(6 * math.pi * f * t) * math.exp(-5 * t))
            smp.append(0.35 * v * math.exp(-2.6 * t) * min(1.0, i / 60))
        save_wav(f"{out}/note_{name}.wav", smp)
    calls = {
        "cow": sweep(150, 115, 1.1, .45, .03, 5, (1, .8, .6, .4), .05),
        "dog": seq([sweep(520, 380, .14, .5, 0, 6, (1, .7, .5), .35), silence(.08), sweep(560, 400, .16, .5, 0, 6, (1, .7, .5), .35)]),
        "cat": sweep(480, 820, .35, .35, .02, 7, (1, .4, .2)) + sweep(820, 520, .35, .35, .02, 7, (1, .4, .2)),
        "sheep": sweep(330, 300, .9, .4, .12, 9, (1, .7, .5, .3), .05),
        "duck": seq([sweep(620, 560, .1, .35, 0, 6, (1, .9, .8, .7), .2), silence(.06)] * 3),
        "bird": seq([sweep(2600, 3600, .07, .25), silence(.04), sweep(3000, 4000, .07, .25), silence(.04), sweep(2800, 3800, .1, .25)]),
        "lion": sweep(140, 90, 1.2, .5, .06, 18, (1, .8, .6, .4), .55),
        "horse": sweep(950, 420, .9, .35, .09, 14, (1, .5, .3)),
        "frog": seq([sweep(210, 180, .07, .45, 0, 6, (1, .8, .6), .3), silence(.05), sweep(260, 200, .12, .45, 0, 6, (1, .8, .6), .3)]),
        "owl": seq([sweep(360, 340, .3, .35), silence(.12), sweep(380, 330, .5, .35)]),
        "rooster": seq([sweep(500, 900, .15, .35, 0, 6, (1, .5)), sweep(900, 1100, .45, .35, .05, 10, (1, .5)), sweep(1100, 600, .3, .35, 0, 6, (1, .5))]),
        "pig": seq([sweep(260, 220, .14, .45, 0, 6, (1, .8, .6), .45), silence(.06), sweep(280, 230, .12, .45, 0, 6, (1, .8, .6), .45)]),
        "elephant": sweep(420, 700, .8, .45, .05, 8, (1, .8, .7, .6, .5), .1),
        "monkey": seq([sweep(700, 1200, .1, .35), sweep(1200, 800, .1, .35)] * 3),
        "bee": sweep(220, 240, 1.0, .25, .05, 30, (1, .9, .8, .7), .1),
        "snake": sweep(5000, 5000, .9, .2, 0, 6, (1,), .95),
    }
    for k, v in calls.items():
        save_wav(f"{out}/animal_{k}.wav", v)


def sounds(out):
    os.makedirs(out, exist_ok=True)
    save_wav(f"{out}/tap.wav", tone([880], 0.06, 0.25, 40))
    save_wav(f"{out}/place.wav", tone([330, 495], 0.12, 0.35, 25))
    save_wav(f"{out}/clear.wav", seq([tone([523], 0.08, .35, 20), tone([659], 0.08, .35, 20), tone([784], 0.16, .35, 12)]))
    save_wav(f"{out}/combo.wav", seq([tone([659, 988], 0.08, .35, 18), tone([784, 1175], 0.08, .35, 18), tone([1047, 1568], 0.2, .35, 10)]))
    save_wav(f"{out}/win.wav", seq([tone([523, 659], .14, .4, 8), tone([659, 784], .14, .4, 8), tone([784, 1047], .4, .4, 4)]))
    save_wav(f"{out}/lose.wav", seq([tone([392], .18, .35, 8), tone([330], .18, .35, 8), tone([262], .4, .35, 5)]))
    save_wav(f"{out}/coin.wav", seq([tone([1319], .05, .3, 30), tone([1760], .15, .3, 18)]))
    save_wav(f"{out}/error.wav", tone([140], .15, .35, 12, "square"))
    save_wav(f"{out}/unlock.wav", seq([tone([784], .07, .3, 20), tone([988], .07, .3, 20), tone([1175], .07, .3, 20), tone([1568], .25, .3, 8)]))
    # 8-second ambient loop (soft pad, C - Am - F - G)
    chords = [[261.6, 329.6, 392.0], [220.0, 261.6, 329.6], [174.6, 220.0, 261.6], [196.0, 246.9, 293.7]]
    music = []
    for c in chords:
        music += tone([f / 2 for f in c] + c, 2.0, 0.18, 0.6)
    save_wav(f"{out}/music.wav", music)
    if MOTIF.startswith("kids"):
        kid_sounds(out)


def main():
    os.makedirs("assets/branding", exist_ok=True)
    os.makedirs("store/screenshots", exist_ok=True)
    ic = icon()
    ic.convert("RGB").save("assets/branding/icon.png")
    foreground().save("assets/branding/icon_foreground.png")
    splash = Image.new("RGBA", (768, 768), (0, 0, 0, 0))
    draw_motif(splash, 384, 384, 520)
    splash.save("assets/branding/splash.png")
    a12 = Image.new("RGBA", (960, 960), (0, 0, 0, 0))
    draw_motif(a12, 480, 480, 520)
    a12.save("assets/branding/splash_android12.png")
    ic.convert("RGB").resize((512, 512)).save("store/icon_512.png")
    for lang in ("tr", "en"):
        feature_graphic(lang).save(f"store/feature_graphic_{lang}.png")
        for i in range(4):
            screenshot(lang, i).save(f"store/screenshots/{lang}_{i + 1}.png")
    sounds("assets/sfx")
    print("assets generated")


if __name__ == "__main__":
    main()
