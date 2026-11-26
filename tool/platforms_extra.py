#!/usr/bin/env python3
"""Ek platform ayarları (CI adımı; `tool/patch_platforms.py`'den sonra çalışır).

Komutlar:
  python tool/platforms_extra.py            -> var olan platform klasörlerini yamalar
  python tool/platforms_extra.py pwa DIR    -> `flutter build web` çıktısını PWA yapar
                                               (çevrimdışı service worker + manifest)

* Android (Chromebook, Google Play Games on PC, tablet): dokunmatik ekran,
  kamera, GPS, sensör, mikrofon ve NFC "zorunlu değil" bildirilir; böylece
  Play bu cihazları filtrelemez. Klavye/fare için etkinlik yeniden
  başlamaz (Flutter şablonu configChanges), pencere boyutu serbest.
* Windows: ilk pencere 1280x800, en küçük 800x600 (tablet düzeni), başlık.
* macOS: ilk pencere 1280x800, en küçük 800x600, App Store kategorisi,
  ağ istemcisi yetkisi, macOS 10.15+, ayrı paket kimliği (.mac).
* Web: manifest (start_url/scope/id) ve çevrimdışı service worker.

Idempotent: her derlemede güvenle çalışır.
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import patch_platforms as _pp  # APP_NAME
    APP_NAME = _pp.APP_NAME
except Exception:  # pragma: no cover
    APP_NAME = "App"

# Mac App Store kategorisi (LSApplicationCategoryType), merkeze göre.
MAC_CATEGORY = {
    "kart": "public.app-category.card-games",
    "masa": "public.app-category.board-games",
    "bulmaca": "public.app-category.puzzle-games",
    "kelime": "public.app-category.word-games",
    "eslestirme": "public.app-category.puzzle-games",
    "zihin": "public.app-category.puzzle-games",
    "bilgi": "public.app-category.trivia-games",
    "strateji": "public.app-category.strategy-games",
    "ozgun": "public.app-category.casual-games",
    "bosta": "public.app-category.simulation-games",
    "arcade": "public.app-category.arcade-games",
    "blok": "public.app-category.puzzle-games",
    "verimlilik": "public.app-category.productivity",
    "finans": "public.app-category.finance",
    "egitim": "public.app-category.education",
}

MIN_W, MIN_H = 800, 600
START_W, START_H = 1280, 800


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def project_name():
    m = re.search(r"^name:\s*(\S+)", read("pubspec.yaml"), re.M)
    return m.group(1) if m else "app"


def hub_key():
    # merkez_kart_oyunlari -> kart
    parts = project_name().split("_")
    return parts[1] if len(parts) > 1 else parts[0]


# --------------------------------------------------------------------------- Android
OPTIONAL_FEATURES = [
    "android.hardware.touchscreen",
    "android.hardware.touchscreen.multitouch",
    "android.hardware.camera",
    "android.hardware.camera.any",
    "android.hardware.camera.autofocus",
    "android.hardware.location",
    "android.hardware.location.gps",
    "android.hardware.location.network",
    "android.hardware.microphone",
    "android.hardware.sensor.accelerometer",
    "android.hardware.sensor.compass",
    "android.hardware.sensor.gyroscope",
    "android.hardware.sensor.stepcounter",
    "android.hardware.sensor.stepdetector",
    "android.hardware.nfc",
    "android.hardware.telephony",
    "android.hardware.wifi",
    "android.hardware.screen.portrait",
    "android.hardware.screen.landscape",
]


def android():
    man = "android/app/src/main/AndroidManifest.xml"
    if not os.path.exists(man):
        return
    s = read(man)
    add = ""
    for f in OPTIONAL_FEATURES:
        if 'android:name="%s"' % f not in s:
            add += '    <uses-feature android:name="%s" android:required="false"/>\n' % f
    if add:
        s = s.replace("<application", add.lstrip() + "    <application", 1)
    # Pencere boyutu serbest (ChromeOS serbest pencere, Play Games on PC).
    if "android:resizeableActivity" not in s:
        s = s.replace("<application", '<application android:resizeableActivity="true"', 1)
    write(man, s)


# --------------------------------------------------------------------------- Windows
def windows():
    main = "windows/runner/main.cpp"
    if os.path.exists(main):
        s = read(main)
        s = re.sub(r"Win32Window::Size size\(\d+, \d+\);", "Win32Window::Size size(%d, %d);" % (START_W, START_H), s)
        s = re.sub(r'window\.Create\(L"[^"]*"', 'window.Create(L"%s"' % APP_NAME.replace('"', ""), s)
        write(main, s)
    win = "windows/runner/win32_window.cpp"
    if os.path.exists(win):
        s = read(win)
        if "WM_GETMINMAXINFO" not in s:
            hook = """    case WM_GETMINMAXINFO: {
      // En küçük pencere %dx%d (mantıksal piksel): tablet düzeni.
      auto info = reinterpret_cast<MINMAXINFO*>(lparam);
      UINT dpi = FlutterDesktopGetDpiForMonitor(MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST));
      double scale = dpi / 96.0;
      info->ptMinTrackSize.x = static_cast<LONG>(%d * scale);
      info->ptMinTrackSize.y = static_cast<LONG>(%d * scale);
      return 0;
    }
""" % (MIN_W, MIN_H, MIN_W, MIN_H)
            s = s.replace("    case WM_DESTROY:", hook + "    case WM_DESTROY:", 1)
        write(win, s)
    rc = "windows/runner/Runner.rc"
    if os.path.exists(rc):
        s = read(rc)
        for key in ("FileDescription", "ProductName"):
            s = re.sub(r'(VALUE "%s", )"[^"]*"' % key, r'\1"%s"' % APP_NAME.replace('"', ""), s)
        s = re.sub(r'(VALUE "CompanyName", )"[^"]*"', r'\1"GameStudio100"', s)
        write(rc, s)


# --------------------------------------------------------------------------- macOS
def macos():
    win = "macos/Runner/MainFlutterWindow.swift"
    if os.path.exists(win):
        s = read(win)
        if "minSize" not in s:
            s = s.replace(
                "    self.setFrame(windowFrame, display: true)\n",
                "    self.setFrame(windowFrame, display: true)\n"
                "    // İlk pencere %dx%d, en küçük %dx%d (tablet düzeni).\n"
                "    self.setContentSize(NSSize(width: %d, height: %d))\n"
                "    self.contentMinSize = NSSize(width: %d, height: %d)\n"
                "    self.center()\n" % (START_W, START_H, MIN_W, MIN_H, START_W, START_H, MIN_W, MIN_H),
                1,
            )
        write(win, s)
    info = "macos/Runner/Configs/AppInfo.xcconfig"
    if os.path.exists(info):
        s = read(info)
        safe = re.sub(r"[^A-Za-z0-9 ]", "", APP_NAME.replace("&", "and")).strip() or "App"
        s = re.sub(r"PRODUCT_NAME = .*", "PRODUCT_NAME = %s" % re.sub(r"\s+", " ", safe), s)
        # Mac App Store'da ayrı (ücretli, tam sürüm) kayıt: iOS uygulamasıyla
        # "universal purchase" olmasın diye paket kimliği .mac ile biter.
        bid = os.environ.get("MACOS_BUNDLE_ID")
        if not bid:
            m = re.search(r"PRODUCT_BUNDLE_IDENTIFIER = (\S+)", s)
            bid = (m.group(1) if m else "com.gamestudio100.app")
            if not bid.endswith(".mac"):
                bid += ".mac"
        s = re.sub(r"PRODUCT_BUNDLE_IDENTIFIER = .*", "PRODUCT_BUNDLE_IDENTIFIER = %s" % bid, s)
        s = re.sub(r"PRODUCT_COPYRIGHT = .*", "PRODUCT_COPYRIGHT = Copyright © 2026 GameStudio100", s)
        write(info, s)
    plist = "macos/Runner/Info.plist"
    if os.path.exists(plist):
        s = read(plist)
        extra = ""
        if "LSApplicationCategoryType" not in s:
            extra += "\t<key>LSApplicationCategoryType</key>\n\t<string>%s</string>\n" % MAC_CATEGORY.get(
                hub_key(), "public.app-category.games")
        if "ITSAppUsesNonExemptEncryption" not in s:
            extra += "\t<key>ITSAppUsesNonExemptEncryption</key>\n\t<false/>\n"
        if extra:
            i = s.rfind("</dict>")
            s = s[:i] + extra + s[i:]
        write(plist, s)
    for ent in ("macos/Runner/Release.entitlements", "macos/Runner/DebugProfile.entitlements"):
        if os.path.exists(ent):
            s = read(ent)
            if "com.apple.security.network.client" not in s:
                i = s.rfind("</dict>")
                s = s[:i] + "\t<key>com.apple.security.network.client</key>\n\t<true/>\n" + s[i:]
            # Dosya seçici (PDF/görsel içe/dışa aktarma) için kullanıcının seçtiği dosyalar.
            if "com.apple.security.files.user-selected.read-write" not in s:
                i = s.rfind("</dict>")
                s = s[:i] + "\t<key>com.apple.security.files.user-selected.read-write</key>\n\t<true/>\n" + s[i:]
            write(ent, s)
    podfile = "macos/Podfile"
    if os.path.exists(podfile):
        s = read(podfile)
        s = re.sub(r"#?\s*platform :osx, '[0-9.]+'", "platform :osx, '10.15'", s, count=1)
        write(podfile, s)
    pbx = "macos/Runner.xcodeproj/project.pbxproj"
    if os.path.exists(pbx):
        s = read(pbx)
        s = re.sub(r"MACOSX_DEPLOYMENT_TARGET = [0-9.]+;", "MACOSX_DEPLOYMENT_TARGET = 10.15;", s)
        write(pbx, s)


# --------------------------------------------------------------------------- Web / PWA
def web_manifest(path):
    if not os.path.exists(path):
        return
    m = json.loads(read(path))
    m.setdefault("id", "./")
    m["start_url"] = "."
    m["scope"] = "."
    m["display"] = "standalone"
    m.setdefault("orientation", "any")
    write(path, json.dumps(m, indent=2, ensure_ascii=False))


SW = r"""// Çevrimdışı service worker (tool/platforms_extra.py üretir).
// Uygulama kabuğu ilk ziyarette önbelleğe alınır; görseller, sesler ve
// yazı tipleri ilk kullanımda. Yeni sürümde eski önbellek silinir.
const VERSION = '%(version)s';
const CACHE = 'gs100-' + VERSION;
const CORE = %(core)s;

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(CORE.map((u) => new Request(u, { cache: 'reload' }))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('gs100-') && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function put(req, res) {
  if (res && (res.ok || res.type === 'opaque')) {
    const copy = res.clone();
    caches.open(CACHE).then((c) => c.put(req, copy));
  }
  return res;
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const same = url.origin === self.location.origin;
  const fonts = url.hostname === 'fonts.gstatic.com' || url.hostname === 'fonts.googleapis.com';
  if (!same && !fonts) return;
  const page = req.mode === 'navigate' || url.pathname.endsWith('/') ||
    url.pathname.endsWith('index.html') || url.pathname.endsWith('version.json') ||
    url.pathname.endsWith('manifest.json');
  if (page) {
    // Ağ önce: yeni sürüm hemen gelir; ağ yoksa önbellekteki kabuk.
    event.respondWith(
      fetch(req).then((r) => put(req, r)).catch(() =>
        caches.match(req, { ignoreSearch: true }).then((r) => r || caches.match('./')))
    );
    return;
  }
  // Önbellek önce (sürüm başına önbellek, değişen dosyalar yeni sürümde gelir).
  event.respondWith(
    caches.match(req, { ignoreSearch: true }).then((hit) => hit || fetch(req).then((r) => put(req, r)))
  );
});
"""

REGISTER = """<script>
  // Çevrimdışı oynanış (PWA): tool/platforms_extra.py
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('flutter_service_worker.js', { scope: './' }).catch(function () {});
    });
  }
</script>
"""

CORE_CANDIDATES = [
    "./",
    "index.html",
    "flutter_bootstrap.js",
    "flutter.js",
    "main.dart.js",
    "manifest.json",
    "favicon.png",
    "icons/Icon-192.png",
    "icons/Icon-512.png",
    "icons/Icon-maskable-192.png",
    "icons/Icon-maskable-512.png",
    "assets/AssetManifest.bin",
    "assets/AssetManifest.bin.json",
    "assets/AssetManifest.json",
    "assets/FontManifest.json",
    "assets/fonts/MaterialIcons-Regular.otf",
    "canvaskit/canvaskit.js",
    "canvaskit/canvaskit.wasm",
    "canvaskit/chromium/canvaskit.js",
    "canvaskit/chromium/canvaskit.wasm",
]


def pwa(build):
    """`flutter build web` çıktısını çevrimdışı çalışan PWA yapar."""
    web_manifest(os.path.join(build, "manifest.json"))
    core = [c for c in CORE_CANDIDATES if c == "./" or os.path.exists(os.path.join(build, c))]
    # Ses efektleri küçük ve her oyunda kullanılır: kabukla birlikte alınır.
    sfx = os.path.join(build, "assets", "assets", "sfx")
    if os.path.isdir(sfx):
        core += ["assets/assets/sfx/" + f for f in sorted(os.listdir(sfx)) if f.endswith(".wav")][:80]
    h = hashlib.sha256()
    for c in core:
        p = os.path.join(build, c)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                h.update(f.read())
    version = h.hexdigest()[:16]
    # Flutter'ın kendi service worker dosyasının yerine (aynı ad: hangisi
    # kaydederse kaydetsin bizimki çalışır).
    write(os.path.join(build, "flutter_service_worker.js"), SW % {"version": version, "core": json.dumps(core, indent=2)})
    index = os.path.join(build, "index.html")
    if os.path.exists(index):
        s = read(index)
        if "flutter_service_worker.js', { scope" not in s:
            s = s.replace("</body>", REGISTER + "</body>", 1)
        if 'rel="manifest"' not in s:
            s = s.replace("</head>", '  <link rel="manifest" href="manifest.json">\n</head>', 1)
        if 'name="theme-color"' not in s:
            try:
                color = json.loads(read(os.path.join(build, "manifest.json"))).get("theme_color", "#000000")
            except Exception:
                color = "#000000"
            s = s.replace("</head>", '  <meta name="theme-color" content="%s">\n</head>' % color, 1)
        write(index, s)
    print("PWA: %d core files, version %s" % (len(core), version))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "pwa":
        pwa(sys.argv[2])
    else:
        android()
        windows()
        macos()
        web_manifest("web/manifest.json")
        print("extra platform settings applied")
