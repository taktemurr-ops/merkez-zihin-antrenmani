#!/usr/bin/env python3
"""shots/raw altındaki cihaz görüntülerini mağaza boyutlarına kırpar:
telefon 1080x1920, tablet 16:9, öne çıkan görsel 1024x500."""
import glob, os
from PIL import Image

os.makedirs('shots/store', exist_ok=True)
for p in sorted(glob.glob('shots/raw/*.png')):
    name, _, size = os.path.basename(p)[:-4].partition('__')
    img = Image.open(p).convert('RGB')
    cw, _, ch = size.partition('x')
    w, h = min(int(cw or img.width), img.width), min(int(ch or img.height), img.height)
    img = img.crop((0, 0, w, h))
    if name.startswith('feature_'):
        img = img.resize((1024, 500), Image.LANCZOS)
    elif name.startswith('phone_') and img.width != 1080:
        img = img.resize((1080, round(1080 * h / w)), Image.LANCZOS)
    lang = name.split('_')[1]
    d = f'shots/store/{lang}'
    os.makedirs(d, exist_ok=True)
    img.save(f'{d}/{name}.png', optimize=True)
print('ok', len(glob.glob('shots/store/*/*.png')))
