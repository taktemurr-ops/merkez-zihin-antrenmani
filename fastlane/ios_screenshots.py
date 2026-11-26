#!/usr/bin/env python3
"""Mağaza görsellerinden (store-graphics.zip açılmış hali: <dil>/phone_*.png,
tablet_*.png) App Store ekran görüntüleri üretir.

Kullanım: python fastlane/ios_screenshots.py <sg_klasörü> <çıktı_klasörü>

- iPhone 6.9"/6.7": 1290x2796 (dikey). 1080x1920 görüntü ortalanır, boşluk
  görüntünün kenar rengiyle doldurulur.
- iPad 13": 2732x2048 (yatay). 1920x1080 görüntü ortalanır.
Çıktı: <çıktı>/<App Store dili>/NN_*.png (deliver bu boyutları tanır).
fastlane/metadata/ios altındaki her dil için, varsa eşleşen görseller kullanılır.
"""
import glob
import os
import sys

from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]
META = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metadata", "ios")
ALIAS = {"no": "nb"}
PHONE = (1290, 2796)
IPAD = (2732, 2048)


def edge_color(img, top=True):
    w, h = img.size
    box = (0, 0, w, 6) if top else (0, h - 6, w, h)
    strip = img.crop(box).resize((1, 1), Image.LANCZOS)
    return strip.getpixel((0, 0))


def fit(path, size):
    img = Image.open(path).convert("RGB")
    cw, ch = size
    scale = min(cw / img.width, ch / img.height)
    nw, nh = round(img.width * scale), round(img.height * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", size, edge_color(img))
    x, y = (cw - nw) // 2, (ch - nh) // 2
    if y > 0:
        # Alt boşluk alt kenarın rengiyle.
        canvas.paste(Image.new("RGB", (cw, ch - y - nh), edge_color(img, top=False)), (0, y + nh))
    canvas.paste(img, (x, y))
    return canvas


n = 0
for loc in sorted(os.listdir(META)):
    if not os.path.isdir(os.path.join(META, loc)):
        continue
    code = loc.split("-")[0]
    src = os.path.join(SRC, ALIAS.get(code, code))
    if loc == "zh-Hans":
        src = os.path.join(SRC, "zh")
    if not os.path.isdir(src):
        src = os.path.join(SRC, "en")
    if not os.path.isdir(src):
        continue
    dst = os.path.join(OUT, loc)
    os.makedirs(dst, exist_ok=True)
    phones = sorted(glob.glob(os.path.join(src, "phone_*.png")))[:10]
    tablets = sorted(glob.glob(os.path.join(src, "tablet_*.png")))[:10]
    for i, p in enumerate(phones, 1):
        fit(p, PHONE).save(os.path.join(dst, f"{i:02d}_iPhone_67_{i}.png"))
        n += 1
    for i, p in enumerate(tablets, 1):
        fit(p, IPAD).save(os.path.join(dst, f"{i:02d}_IPAD_PRO_3GEN_129_{i}.png"))
        n += 1
print("ok", n, "screenshots")
