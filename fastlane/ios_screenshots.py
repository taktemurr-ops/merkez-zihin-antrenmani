#!/usr/bin/env python3
"""store-graphics.zip'ten (açılmış hali) App Store ekran görüntülerini hazırlar.

Kullanım: python fastlane/ios_screenshots.py <sg_klasörü> <çıktı_klasörü>

Yalnız ÇERÇEVESİZ (tam ekran) iOS görselleri kullanılır. Play için üretilen
genel cihaz çerçeveli phone_*/tablet_* görselleri App Store'a gönderilmez
(Apple Kural 2.3.3: ekran görüntüsü uygulamanın kendisini göstermeli; Apple
dışı/genel cihaz çizimi reddedilebilir). Üstteki başlık bandı serbesttir.

Kaynak düzenleri (store-shots iş akışı üretir):
- oyun merkezleri:      <sg>/<dil>/iosphone_<dil>_N.png, iospad_<dil>_N.png
- uygulama merkezleri:  <sg>/appstore/<App Store yereli>/N_iphone69.png, N_ipad13.png

Boyutlar (piksel, birebir denetlenir; uymayan görsel hata verir):
- iPhone 6,9": 1290x2796 (dikey)
- iPad 13":    2732x2048 (yatay) ya da 2048x2732 (dikey)

Çıktı: <çıktı>/<App Store yereli>/NN_iPhone_69_N.png, NN_iPad_13_N.png
(deliver cihazı piksel boyutundan tanır). Çerçevesiz görsel yoksa hiçbir şey
yazılmaz; yalnız metinler yüklenir (store-shots iş akışını çalıştırın).
"""
import glob
import os
import re
import sys

from PIL import Image

PHONE = {(1290, 2796)}
IPAD = {(2732, 2048), (2048, 2732)}
ALIAS = {"no": "nb"}


def num(path):
    m = re.findall(r"\d+", os.path.basename(path))
    return int(m[-1]) if m else 0


def game_layout(sg, loc):
    code = loc.split("-")[0]
    lang = "zh" if loc.startswith("zh") else ALIAS.get(code, code)
    for d in (os.path.join(sg, lang), os.path.join(sg, "en")):
        phones = sorted(glob.glob(os.path.join(d, "iosphone_*.png")), key=num)
        pads = sorted(glob.glob(os.path.join(d, "iospad_*.png")), key=num)
        if phones or pads:
            return phones, pads
    return [], []


def app_layout(sg, loc):
    for name in (loc, "en-US"):
        d = os.path.join(sg, "appstore", name)
        phones = sorted(glob.glob(os.path.join(d, "*_iphone69.png")), key=num)
        pads = sorted(glob.glob(os.path.join(d, "*_ipad13.png")), key=num)
        if phones or pads:
            return phones, pads
    return [], []


def main(sg, out, meta):
    n, bad = 0, []
    for loc in sorted(os.listdir(meta)):
        if not os.path.isdir(os.path.join(meta, loc)):
            continue
        phones, pads = app_layout(sg, loc) if os.path.isdir(os.path.join(sg, "appstore")) else game_layout(sg, loc)
        if not phones and not pads:
            continue
        dst = os.path.join(out, loc)
        os.makedirs(dst, exist_ok=True)
        for kind, files, sizes, tag in (("iPhone", phones, PHONE, "iPhone_69"), ("iPad", pads, IPAD, "iPad_13")):
            for i, p in enumerate(files[:10], 1):
                img = Image.open(p)
                if img.size not in sizes:
                    bad.append(f"{p}: {img.size[0]}x{img.size[1]} ({kind} için {' / '.join('%dx%d' % s for s in sorted(sizes))} gerekir)")
                    continue
                img.convert("RGB").save(os.path.join(dst, f"{i:02d}_{tag}_{i}.png"), optimize=True)
                n += 1
    if bad:
        print("HATA: boyutu uymayan görseller:\n  " + "\n  ".join(bad))
        return 2
    if n == 0:
        print("::warning::store-graphics.zip içinde çerçevesiz iOS görseli yok "
              "(store-shots iş akışını yeniden çalıştırın); App Store'a yalnız metinler gönderilir.")
        return 0
    print("ok", n, "screenshots")
    return 0


if __name__ == "__main__":
    META = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metadata", "ios")
    sys.exit(main(sys.argv[1], sys.argv[2], META))
