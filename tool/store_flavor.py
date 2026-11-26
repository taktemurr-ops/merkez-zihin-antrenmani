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
  (--dart-define=STORE=... ve tablodaki reklam kimliği değişkenleri).

Google Play derlemesi bu betiği çalıştırmaz (değişiklik yok).
"""
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
    if "tools:replace" not in s:
        s = s.replace("<application", '<application tools:replace="android:usesCleartextTraffic"', 1)
    write(man, s)


def store_config(spec):
    cfg = spec.get("config_secret")
    if not cfg:
        return None
    raw = os.environ.get(cfg["env"], "").strip()
    if not raw:
        print("%s tanımlı değil: %s test kipinde derleniyor (yapılandırma dosyası yok)." % (cfg["env"], spec["name"]))
        return None
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


HOOKS = {"huawei": patch_huawei}


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
    patch_pubspec(spec, ref)
    patch_dart(spec)
    patch_gradle_root(spec)
    if not spec.get("gms"):
        patch_no_gms()
    patch_manifest_common(spec)
    cfg = store_config(spec)
    if store in HOOKS:
        HOOKS[store](spec, cfg)
    env = os.environ.get("GITHUB_ENV")
    if env:
        with open(env, "a", encoding="utf-8") as f:
            defs = ["--dart-define=STORE=%s" % store]
            defs += ["--dart-define=%s=%s" % (k, os.environ[k]) for k in spec.get("ad_defines", []) if os.environ.get(k)]
            f.write("STORE_ID=%s\nSTORE_SUFFIX=%s\nSTORE_DEFS=%s\n" % (store, spec["artifact_suffix"], " ".join(defs)))
    print("%s derlemesi hazır (studio-core %s, ek '%s')" % (spec["name"], ref[:7], spec["artifact_suffix"]))


if __name__ == "__main__":
    main()
