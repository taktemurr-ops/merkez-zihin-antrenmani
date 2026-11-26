#!/usr/bin/env python3
"""Mağaza görsellerini (store-graphics.zip açılmış hali) ve uygulama simgesini
fastlane supply'ın beklediği yere koyar:

fastlane/metadata/android/<yerel>/images/
    icon.png                      (store/icon_512.png, 512x512)
    featureGraphic.png            (1024x500)
    phoneScreenshots/*.png        (en çok 8)
    sevenInchScreenshots/*.png    (tablet görselleri, en çok 8)
    tenInchScreenshots/*.png      (tablet görselleri, en çok 8)

İki kaynak düzeni okunur (store-shots iş akışı üretir):
- oyun merkezleri:      <sg>/<dil>/{phone_*,tablet_*,feature_*}.png
- uygulama merkezleri:  <sg>/android/<Play yereli>/images/{phoneScreenshots/,tenInchScreenshots/,featureGraphic.png}
Bir yerel için görsel yoksa en-US / en görselleri kullanılır.
App Store'a özgü görseller (iosphone_*, iospad_*, appstore/, ios/) atlanır.

Kullanım: python tool/play_prepare.py <sg_klasörü>
Çıkış kodu: hiç görsel bulunamazsa 1 (iş akışı bu durumda görsel eşitlemez).
"""
import glob
import os
import re
import shutil
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else 'sg'
META = 'fastlane/metadata/android'
ALIAS = {'he': 'iw', 'nb': 'no'}  # oyun düzeni: dil kodu -> Play yerel öneki
MAX = 8


def num(p):
    m = re.findall(r'\d+', os.path.basename(p))
    return int(m[-1]) if m else 0


def game_sources():
    """Play yerel öneki -> (telefon, tablet, öne çıkan)."""
    out = {}
    for lang in sorted(os.listdir(SRC)):
        d = os.path.join(SRC, lang)
        if not os.path.isdir(d) or lang in ('android', 'ios', 'appstore'):
            continue
        phones = sorted(glob.glob(os.path.join(d, 'phone_*.png')), key=num)
        tablets = sorted(glob.glob(os.path.join(d, 'tablet_*.png')), key=num)
        feat = (glob.glob(os.path.join(d, 'feature_*.png')) or [None])[0]
        out[ALIAS.get(lang, lang)] = (phones, tablets, feat)
    return out


def app_sources():
    out = {}
    base = os.path.join(SRC, 'android')
    for loc in sorted(os.listdir(base)):
        img = os.path.join(base, loc, 'images')
        if not os.path.isdir(img):
            continue
        phones = sorted(glob.glob(os.path.join(img, 'phoneScreenshots', '*.png')), key=num)
        tablets = sorted(glob.glob(os.path.join(img, 'tenInchScreenshots', '*.png')), key=num)
        feat = os.path.join(img, 'featureGraphic.png')
        out[loc] = (phones, tablets, feat if os.path.exists(feat) else None)
    return out


def pick(sources, loc, app):
    keys = [loc] if app else [loc.split('-')[0]]
    keys += ['en-US', 'en']
    for k in keys:
        if k in sources and sources[k][0]:
            return k, sources[k]
    return None, ([], [], None)


app = os.path.isdir(os.path.join(SRC, 'android'))
sources = app_sources() if app else game_sources()
locales = sorted(d for d in os.listdir(META) if os.path.isdir(os.path.join(META, d)))
total, fallback = 0, []
for loc in locales:
    used, (phones, tablets, feat) = pick(sources, loc, app)
    img = os.path.join(META, loc, 'images')
    shutil.rmtree(img, ignore_errors=True)
    os.makedirs(img)
    if os.path.exists('store/icon_512.png'):
        shutil.copy('store/icon_512.png', os.path.join(img, 'icon.png'))
    if used is None:
        continue
    if used not in (loc, loc.split('-')[0]):
        fallback.append(f'{loc}<-{used}')
    if feat:
        shutil.copy(feat, os.path.join(img, 'featureGraphic.png'))
        total += 1
    for folder, files in (('phoneScreenshots', phones), ('sevenInchScreenshots', tablets),
                          ('tenInchScreenshots', tablets)):
        if not files:
            continue
        os.makedirs(os.path.join(img, folder))
        for i, f in enumerate(files[:MAX], 1):
            shutil.copy(f, os.path.join(img, folder, f'{i:02d}.png'))
            total += 1
print('ok', total, 'images,', len(locales), 'locales', '(app layout)' if app else '(game layout)',
      ('fallback: ' + ', '.join(fallback)) if fallback else '')
sys.exit(0 if total else 1)
