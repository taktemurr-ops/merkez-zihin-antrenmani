#!/usr/bin/env python3
"""Mağaza görsellerini (store-graphics.zip açılmış hali: sg/<dil>/...) ve
uygulama simgesini fastlane'in beklediği yerlere koyar:
fastlane/metadata/android/<yerel>/images/{icon.png, featureGraphic.png,
phoneScreenshots/, tenInchScreenshots/}."""
import glob, os, shutil, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else 'sg'
META = 'fastlane/metadata/android'
ALIAS = {'he': 'iw', 'nb': 'no'}
locales = sorted(d for d in os.listdir(META) if os.path.isdir(os.path.join(META, d)))
n = 0
for lang in sorted(os.listdir(SRC)):
    src = os.path.join(SRC, lang)
    if not os.path.isdir(src):
        continue
    code = ALIAS.get(lang, lang)
    locs = [l for l in locales if l.split('-')[0] == code]
    for loc in locs:
        img = os.path.join(META, loc, 'images')
        shutil.rmtree(img, ignore_errors=True)
        os.makedirs(os.path.join(img, 'phoneScreenshots'))
        os.makedirs(os.path.join(img, 'tenInchScreenshots'))
        if os.path.exists('store/icon_512.png'):
            shutil.copy('store/icon_512.png', os.path.join(img, 'icon.png'))
        for f in sorted(glob.glob(os.path.join(src, '*.png'))):
            b = os.path.basename(f)
            if b.startswith('feature_'):
                shutil.copy(f, os.path.join(img, 'featureGraphic.png'))
            elif b.startswith('phone_'):
                shutil.copy(f, os.path.join(img, 'phoneScreenshots', b))
            elif b.startswith('tablet_'):
                shutil.copy(f, os.path.join(img, 'tenInchScreenshots', b))
            n += 1
print('ok', n, 'images')
