#!/usr/bin/env python3
"""Mağaza derlemesi (flavor) yaması: `python tool/store_flavor.py <store>`.

`flutter create` + `tool/patch_platforms.py` SONRASINDA, `flutter pub get`
ÖNCESİNDE çalışır. Mağaza özellikleri tek kaynaktan, studio-core'un
`tool/stores.json` tablosundan okunur (pubspec.yaml'daki sabitlenmiş
studio_core SHA'sı). Derleme `--dart-define=STORE=<store>` ile yapılır.

Yaptıkları (tabloya göre):
* plugin: studio-core/packages/<plugin> paketini pubspec'e ekler ve
  lib/store_flavor.dart dosyasını o paketin register...() çağrısıyla yazar;
* maven: Android Maven depoları (ör. Huawei) eklenir; eski eklentiler için
  eksik `namespace` tamamlanır;
* gms=false: ML Kit Play hizmetleri sürümleri yerine gömülü modeller
  (metin tanıma Latin/Çince/Devanagari/Japonca/Korece, barkod), mobile_scanner
  gömülü model; Play hizmetlerine özgü meta veriler kaldırılır;
* config_secret: mağaza yapılandırma dosyası (ör. agconnect-services.json)
  gizli değişkenden yazılır; yoksa derleme test kipinde yine başarılı olur.
* GITHUB_ENV: STORE_ID, STORE_SUFFIX (çıktı dosya adı eki), STORE_DEFS
  (--dart-define=STORE=... ve tablodaki reklam kimliği / extra_defines
  değişkenleri).
* tv: Android TV / Fire TV (leanback başlatıcısı, 320x180 afiş, dokunmatik
  isteğe bağlı, `studio/device` algılama kanalı); yalnızca `tv_hubs`.
* Mağazaya özgü kancalar (HOOKS): huawei (HMS R8, app id), samsung (Samsung
  IAP SDK AAR'ı SAMSUNG_IAP_AAR_URL'den), onestore (<queries>, R8).

`python tool/store_flavor.py google --tv-only` Google Play derlemesinde
yalnızca televizyon yamasını uygular (Android TV, Play).

Google Play derlemesi bu betiği çalıştırmaz (değişiklik yok).
"""
import hashlib
import json
import os
import re
import sys
import urllib.request

CORE_URL = "https://raw.githubusercontent.com/taktemurr-ops/studio-core/%s/tool/stores.json"


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def core_ref():
    s = read("pubspec.yaml")
    refs = re.findall(r"url: https://github.com/taktemurr-ops/studio-core\n\s+ref: ([0-9a-f]{7,40})", s)
    if not refs:
        sys.exit("pubspec.yaml: studio_core ref bulunamadı")
    return refs[-1]  # dependency_overrides (en sonda) geçerlidir


def load_table(ref):
    local = os.environ.get("STORES_JSON")
    if local:
        return json.loads(read(local))
    for i in range(3):
        try:
            with urllib.request.urlopen(CORE_URL % ref, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # ağ hatası: tekrar dene
            err = e
    sys.exit("stores.json alınamadı: %s" % err)


def patch_pubspec(spec, ref):
    plugin = spec.get("plugin")
    if not plugin:
        return
    s = read("pubspec.yaml")
    name = plugin["package"]
    if re.search(r"^  %s:" % name, s, re.M):
        return
    dep = (
        "  # %s derlemesi (tool/store_flavor.py ekler; depoda yok)\n"
        "  %s:\n    git:\n      url: https://github.com/taktemurr-ops/studio-core\n"
        "      ref: %s\n      path: %s\n" % (spec["name"], name, ref, plugin["path"])
    )
    s = s.replace("dependencies:\n  flutter:\n    sdk: flutter\n", "dependencies:\n  flutter:\n    sdk: flutter\n" + dep, 1)
    if dep not in s:
        sys.exit("pubspec.yaml: dependencies bölümü bulunamadı")
    write("pubspec.yaml", s)


def patch_dart(spec):
    plugin = spec.get("plugin")
    body = "/// %s derlemesi: tool/store_flavor.py yazdı.\n" % spec["name"]
    if plugin:
        body += "import '%s';\n\nvoid registerStoreFlavor() => %s();\n" % (plugin["import"], plugin["register"])
    else:
        body += "void registerStoreFlavor() {}\n"
    write("lib/store_flavor.dart", body)


NAMESPACE_FIX = """
// Eski Android eklentileri (ör. HMS) için eksik namespace (tool/store_flavor.py).
subprojects {
    plugins.withId("com.android.library") {
        val ext = extensions.findByName("android")
        if (ext != null) {
            val ns = ext.javaClass.getMethod("getNamespace").invoke(ext)
            if (ns == null) {
                ext.javaClass.getMethod("setNamespace", String::class.java).invoke(ext, project.group.toString())
            }
        }
    }
}
"""


def patch_gradle_root(spec):
    for p in ("android/build.gradle.kts", "android/build.gradle"):
        if not os.path.exists(p):
            continue
        s = read(p)
        kts = p.endswith(".kts")
        for url in spec.get("maven", []):
            if url in s:
                continue
            line = ('        maven { url = uri("%s") }\n' if kts else "        maven { url '%s' }\n") % url
            s, n = re.subn(r"(allprojects\s*\{\s*repositories\s*\{\s*\n)", r"\g<1>" + line.replace("\\", "\\\\"), s, count=1)
            if n == 0:
                s += "\nallprojects {\n    repositories {\n%s    }\n}\n" % line
        if spec.get("plugin") and kts and "setNamespace" not in s:
            s = s.replace("subprojects {", NAMESPACE_FIX.strip() + "\n\nsubprojects {", 1) if "subprojects {" in s else s + NAMESPACE_FIX
        write(p, s)
    st = "android/settings.gradle.kts"
    if os.path.exists(st):
        s = read(st)
        for url in spec.get("maven", []):
            if url not in s and "pluginManagement" in s:
                s = re.sub(r"(pluginManagement\s*\{[\s\S]*?repositories\s*\{\s*\n)", r'\g<1>        maven { url = uri("%s") }\n' % url, s, count=1)
        write(st, s)


BUNDLED_ML = """
// GMS'siz derleme (tool/store_flavor.py): ML Kit modelleri APK'ya gömülü.
dependencies {
    implementation("com.google.mlkit:text-recognition-chinese:16.0.1")
    implementation("com.google.mlkit:text-recognition-devanagari:16.0.1")
    implementation("com.google.mlkit:text-recognition-japanese:16.0.1")
    implementation("com.google.mlkit:text-recognition-korean:16.0.1")
}
"""


def patch_no_gms():
    props = "android/gradle.properties"
    if os.path.exists(props):
        p = read(props)
        p2 = re.sub(r"\n?dev\.steenbakker\.mobile_scanner\.useUnbundled=true\n?", "\n", p)
        if p2 != p:
            write(props, p2)
    gradle = "android/app/build.gradle.kts"
    if os.path.exists(gradle):
        s = read(gradle)
        if "play-services-mlkit-text-recognition" in s:
            s = re.sub(r'\nconfigurations\.all \{\s*exclude\(group = "com\.google\.mlkit", module = "text-recognition"\)\s*\}\n', "\n", s)
            s = re.sub(r'\ndependencies \{\n(\s*implementation\("com\.google\.android\.gms:play-services-mlkit[^\n]*\n)+\}\n', "\n", s)
            if "play-services-mlkit" in s:
                sys.exit("build.gradle.kts: Play hizmetleri ML Kit bloğu kaldırılamadı")
            s += BUNDLED_ML
            write(gradle, s)
    man = "android/app/src/main/AndroidManifest.xml"
    if os.path.exists(man):
        s = read(man)
        s = re.sub(r'\s*<meta-data android:name="com\.google\.mlkit\.vision\.DEPENDENCIES"[^>]*/>', "", s)
        write(man, s)


def patch_manifest_common(spec):
    man = "android/app/src/main/AndroidManifest.xml"
    if not os.path.exists(man) or not spec.get("plugin"):
        return
    s = read(man)
    # Eklenti manifestleri usesCleartextTraffic="true" bildirebilir; uygulama
    # yalnızca HTTPS kullanır (network_security_config), bizim değer kalır.
    if "xmlns:tools" not in s:
        s = s.replace("<manifest ", '<manifest xmlns:tools="http://schemas.android.com/tools" ', 1)
    # Yalnızca <application> öğesine bakılır (izinlerde başka tools:replace olabilir).
    m = re.search(r"<application\b[^>]*>", s)
    if m and "android:usesCleartextTraffic" not in (re.search(r'tools:replace="([^"]*)"', m.group(0)) or [None, ""])[1]:
        tag = m.group(0)
        r = re.search(r'tools:replace="([^"]*)"', tag)
        if r:
            tag2 = tag.replace(r.group(0), 'tools:replace="%s,android:usesCleartextTraffic"' % r.group(1), 1)
        else:
            tag2 = tag.replace("<application", '<application tools:replace="android:usesCleartextTraffic"', 1)
        s = s[: m.start()] + tag2 + s[m.end():]
    write(man, s)


def store_config(spec):
    cfg = spec.get("config_secret")
    if not cfg:
        return None
    raw = os.environ.get(cfg["env"], "").strip()
    if not raw:
        print("%s tanımlı değil: %s test kipinde derleniyor (yapılandırma dosyası yok)." % (cfg["env"], spec["name"]))
        return None
    if cfg.get("assets_only"):
        # JSON olmayan dosya (ör. Amazon AppstoreAuthenticationKey.pem): yalnızca assets.
        write(os.path.join("android/app/src/main/assets", cfg["file"]), raw + "\n")
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        sys.exit("%s geçerli JSON değil" % cfg["env"])
    write(os.path.join("android/app", cfg["file"]), raw)
    write(os.path.join("android/app/src/main/assets", cfg["file"]), raw)
    return data


HMS_RULES = """
# HMS Core (tool/store_flavor.py): Huawei'nin önerdiği R8 kuralları; isteğe
# bağlı HMS modülleri (HiAnalytics, tam IAP, Cronet) derlemede yoktur.
-keepattributes *Annotation*,Exceptions,InnerClasses,Signature,SourceFile,LineNumberTable
-keep class com.huawei.hianalytics.** { *; }
-keep class com.huawei.updatesdk.** { *; }
-keep class com.huawei.hms.** { *; }
-keep class com.huawei.agconnect.** { *; }
-keep class com.huawei.openalliance.ad.** { *; }
-dontwarn com.huawei.**
-dontwarn org.chromium.net.**
-dontwarn javax.xml.stream.**
-dontwarn org.apache.tika.**
"""


def patch_huawei(spec, cfg):
    rules = "android/app/proguard-rules.pro"
    old = read(rules) if os.path.exists(rules) else ""
    if "com.huawei.hms.**" not in old:
        write(rules, old + HMS_RULES)
    man = "android/app/src/main/AndroidManifest.xml"
    if not os.path.exists(man):
        return
    s = read(man)
    app_id = ""
    if cfg:
        app_id = str((cfg.get("client") or {}).get("app_id") or (cfg.get("app_info") or {}).get("app_id") or "")
    if app_id and "com.huawei.hms.client.appid" not in s:
        s = s.replace(
            "</application>",
            '    <meta-data android:name="com.huawei.hms.client.appid" android:value="appid=%s"/>\n    </application>' % app_id,
            1,
        )
    write(man, s)


# ---- Samsung Galaxy Store ------------------------------------------------------

SAMSUNG_GRADLE = """
// Samsung IAP SDK (tool/store_flavor.py; SAMSUNG_IAP_AAR_URL gizli değişkeninden).
dependencies {
    implementation(files("libs/samsung-iap.aar"))
}
"""


def patch_samsung(spec, cfg):
    """Samsung IAP SDK AAR'ı (Samsung hesabıyla indirilir, herkese açık Maven'de
    yok) SAMSUNG_IAP_AAR_URL'den indirilir; yoksa studio_samsung "stub"
    kaynaklarıyla derlenir (satın alma kapalı, AdMob açık)."""
    url = os.environ.get("SAMSUNG_IAP_AAR_URL", "").strip()
    if not url:
        print("SAMSUNG_IAP_AAR_URL tanımlı değil: Galaxy Store derlemesi Samsung IAP olmadan (yalnızca reklam).")
        return
    if not url.startswith("https://"):
        sys.exit("SAMSUNG_IAP_AAR_URL https:// ile başlamalı")
    dest = os.path.abspath("android/app/libs/samsung-iap.aar")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    want = os.environ.get("SAMSUNG_IAP_AAR_SHA256", "").strip().lower()
    got = hashlib.sha256(data).hexdigest()
    if want and want != got:
        sys.exit("Samsung IAP AAR SHA-256 uyuşmuyor (%s)" % got)
    if not data.startswith(b"PK"):
        sys.exit("SAMSUNG_IAP_AAR_URL bir AAR (zip) döndürmedi")
    with open(dest, "wb") as f:
        f.write(data)
    gradle = "android/app/build.gradle.kts"
    s = read(gradle)
    if "samsung-iap.aar" not in s:
        write(gradle, s + SAMSUNG_GRADLE)
    env = os.environ.get("GITHUB_ENV")
    if env:
        with open(env, "a", encoding="utf-8") as f:
            f.write("SAMSUNG_IAP_AAR=%s\n" % dest)
    os.environ["SAMSUNG_IAP_AAR"] = dest
    print("Samsung IAP SDK eklendi (sha256 %s)" % got[:12])


# ---- ONE store -------------------------------------------------------------------

ONESTORE_QUERIES = """    <queries>
        <intent>
            <action android:name="com.onestore.ipc.iap.IapService.ACTION" />
        </intent>
        <intent>
            <action android:name="android.intent.action.VIEW" />
            <data android:scheme="onestore" />
        </intent>
    </queries>
"""

ONESTORE_RULES = """
# ONE store IAP / lisans (tool/store_flavor.py; ONE store'un önerdiği kurallar).
-keep class com.gaa.sdk.base.** { *; }
-keep class com.gaa.sdk.auth.** { *; }
-keep class com.gaa.sdk.iap.** { *; }
-keep class com.onestore.extern.licensing.** { *; }
-dontwarn com.gaa.sdk.**
"""


def patch_onestore(spec, cfg):
    man = "android/app/src/main/AndroidManifest.xml"
    s = read(man)
    if "com.onestore.ipc.iap.IapService.ACTION" not in s:
        s = s.replace("<application", ONESTORE_QUERIES + "    <application", 1)
        write(man, s)
    rules = "android/app/proguard-rules.pro"
    old = read(rules) if os.path.exists(rules) else ""
    if "com.gaa.sdk.iap" not in old:
        write(rules, old + ONESTORE_RULES)


# ---- Amazon Appstore ----------------------------------------------------------------


def patch_amazon(spec, cfg):
    # Fire OS: Google Play hizmetleri yok; AdMob uygulama kimliği meta verisi
    # zararsız kalır (AdMob hiç başlatılmaz). Fire TV kumandası için dokunmatik
    # zorunlu değildir (patch_tv). Ortak anahtar (AppstoreAuthenticationKey.pem)
    # config_secret ile assets'e yazılır.
    pass


# ---- Televizyon (Android TV / Google TV, Fire TV) -----------------------------------

TV_KT = """
    // Televizyon algılama (tool/store_flavor.py): studio_core TvMode.
    private fun studioIsTv(): Boolean {
        val ui = getSystemService(android.content.Context.UI_MODE_SERVICE) as android.app.UiModeManager
        val pm = packageManager
        return ui.currentModeType == android.content.res.Configuration.UI_MODE_TYPE_TELEVISION ||
            pm.hasSystemFeature("android.software.leanback") ||
            pm.hasSystemFeature("amazon.hardware.fire_tv")
    }
"""

TV_REGISTER = """io.flutter.plugin.common.MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "studio/device")
            .setMethodCallHandler { call, result ->
                if (call.method == "isTv") result.success(studioIsTv()) else result.notImplemented()
            }"""


def _hub_id():
    s = read("pubspec.yaml")
    m = re.search(r"^name:\s*(\S+)", s, re.M)
    return m.group(1).replace("_", "-") if m else ""


def _tv_banner():
    """320x180 leanback afişi: simge + uygulama adı (tool/patch_platforms.py APP_NAME)."""
    out = "android/app/src/main/res/drawable-xhdpi/tv_banner.png"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    name = ""
    if os.path.exists("tool/patch_platforms.py"):
        m = re.search(r'^APP_NAME\s*=\s*"([^"]+)"', read("tool/patch_platforms.py"), re.M)
        name = m.group(1) if m else ""
    bg = "#283593"
    m = re.search(r'adaptive_icon_background:\s*"(#[0-9A-Fa-f]{6})"', read("pubspec.yaml"))
    if m:
        bg = m.group(1)
    icon = "assets/branding/icon.png"
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        Image = None
    if Image is None:
        if not os.path.exists(icon):
            sys.exit("TV afişi için Pillow ya da %s gerekli" % icon)
        with open(icon, "rb") as f, open(out, "wb") as g:
            g.write(f.read())
        return
    img = Image.new("RGB", (320, 180), bg)
    if os.path.exists(icon):
        ic = Image.open(icon).convert("RGBA").resize((120, 120))
        img.paste(ic, (20, 30), ic)
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=26)
    except TypeError:
        font = ImageFont.load_default()
    words, lines, cur = name.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) > 160 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    y = 90 - 16 * len(lines)
    for ln in lines[:3]:
        d.text((150, y), ln, fill="white", font=font)
        y += 32
    img.save(out)


def patch_tv(table, spec):
    """Leanback başlatıcısı, afiş, dokunmatik isteğe bağlı ve TV algılama
    kanalı: yalnızca stores.json `tv_hubs` merkezlerinde ve `tv: true`
    mağazalarında (Google Play -> Android TV, Amazon -> Fire TV)."""
    hub = _hub_id()
    if not spec.get("tv") or hub not in table.get("tv_hubs", []):
        return False
    man = "android/app/src/main/AndroidManifest.xml"
    s = read(man)
    for feat in ("android.software.leanback", "android.hardware.touchscreen", "android.hardware.faketouch"):
        if 'android:name="%s"' % feat not in s:
            s = s.replace("<application", '<uses-feature android:name="%s" android:required="false"/>\n    <application' % feat, 1)
    if "android:banner" not in s:
        s = s.replace("<application", '<application android:banner="@drawable/tv_banner"', 1)
    if "LEANBACK_LAUNCHER" not in s:
        s, n = re.subn(
            r'(<category android:name="android.intent.category.LAUNCHER"\s*/>)',
            r'\1\n                <category android:name="android.intent.category.LEANBACK_LAUNCHER"/>',
            s,
            count=1,
        )
        if n == 0:
            sys.exit("AndroidManifest.xml: LAUNCHER kategorisi bulunamadı")
    write(man, s)
    _tv_banner()
    for d, _, files in os.walk("android/app/src/main"):
        for f in files:
            if f != "MainActivity.kt":
                continue
            p = os.path.join(d, f)
            k = read(p)
            if "studio/device" in k:
                continue
            if "configureFlutterEngine" in k:
                k = k.replace(
                    "super.configureFlutterEngine(flutterEngine)",
                    "super.configureFlutterEngine(flutterEngine)\n        " + TV_REGISTER,
                    1,
                )
                k = k.rstrip()
                assert k.endswith("}")
                k = k[:-1] + TV_KT + "}\n"
            else:
                m = re.search(r"class MainActivity\s*:\s*(\w+)\(\)\s*(\{\s*\})?", k)
                if not m:
                    sys.exit("MainActivity.kt tanınmadı")
                body = (
                    "class MainActivity : %s() {\n"
                    "    override fun configureFlutterEngine(flutterEngine: io.flutter.embedding.engine.FlutterEngine) {\n"
                    "        super.configureFlutterEngine(flutterEngine)\n        %s\n    }\n%s}\n"
                ) % (m.group(1), TV_REGISTER, TV_KT)
                k = k[: m.start()] + body + k[m.end():]
            write(p, k)
    print("Televizyon: leanback başlatıcısı, afiş ve algılama kanalı eklendi (%s)" % hub)
    return True


HOOKS = {"huawei": patch_huawei, "samsung": patch_samsung, "onestore": patch_onestore, "amazon": patch_amazon}


def main():
    if len(sys.argv) < 2:
        sys.exit("kullanım: tool/store_flavor.py <store>")
    store = sys.argv[1]
    ref = core_ref()
    table = load_table(ref)
    specs = {s["id"]: s for s in table["stores"]}
    if store not in specs:
        sys.exit("bilinmeyen mağaza: %s (%s)" % (store, ", ".join(specs)))
    spec = specs[store]
    if spec.get("platform") != "android":
        sys.exit("%s bir Android mağazası değil" % store)
    if "--tv-only" in sys.argv[2:]:
        # Google Play derlemesi: yalnızca Android TV yaması.
        patch_tv(table, spec)
        return
    patch_pubspec(spec, ref)
    patch_dart(spec)
    patch_gradle_root(spec)
    if not spec.get("gms"):
        patch_no_gms()
    patch_manifest_common(spec)
    cfg = store_config(spec)
    if store in HOOKS:
        HOOKS[store](spec, cfg)
    patch_tv(table, spec)
    env = os.environ.get("GITHUB_ENV")
    if env:
        with open(env, "a", encoding="utf-8") as f:
            defs = ["--dart-define=STORE=%s" % store]
            defs += ["--dart-define=%s=%s" % (k, os.environ[k])
                     for k in spec.get("ad_defines", []) + spec.get("extra_defines", []) if os.environ.get(k)]
            f.write("STORE_ID=%s\nSTORE_SUFFIX=%s\nSTORE_DEFS=%s\n" % (store, spec["artifact_suffix"], " ".join(defs)))
    print("%s derlemesi hazır (studio-core %s, ek '%s')" % (spec["name"], ref[:7], spec["artifact_suffix"]))


if __name__ == "__main__":
    main()
