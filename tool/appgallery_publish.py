#!/usr/bin/env python3
"""AppGallery Connect Publishing API ile yükleme (bkz. .github/workflows/appgallery.yml).

  python tool/appgallery_publish.py --check
      Mağaza metinlerini (fastlane/metadata/android, 33 dil) AppGallery
      biçimine çevirir, uzunlukları denetler, store/appgallery/listing.json
      yazar. Ağ gerekmez; CI'da her derlemede çalışır.

  python tool/appgallery_publish.py --file app.aab [--listing] [--submit]
      HUAWEI_CLIENT_ID / HUAWEI_CLIENT_SECRET / HUAWEI_APP_ID ortam
      değişkenleriyle: paketi yükler, istenirse 33 dilde mağaza metinlerini
      günceller ve incelemeye gönderir. Değişkenler yoksa temiz biçimde atlar.

Gizli değerler hiçbir zaman yazdırılmaz.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://connect-api.cloud.huawei.com/api"
META = "fastlane/metadata/android"
# Google Play yerel kodu -> AppGallery dil kodu (yalnızca İbranice farklı).
LANG = {
    "ar": "ar", "bn-BD": "bn-BD", "cs-CZ": "cs-CZ", "da-DK": "da-DK", "de-DE": "de-DE",
    "el-GR": "el-GR", "en-US": "en-US", "es-ES": "es-ES", "fa": "fa", "fi-FI": "fi-FI",
    "fil": "fil", "fr-FR": "fr-FR", "hi-IN": "hi-IN", "hu-HU": "hu-HU", "id": "id",
    "it-IT": "it-IT", "iw-IL": "he_IL", "ja-JP": "ja-JP", "ko-KR": "ko-KR", "ms": "ms",
    "nl-NL": "nl-NL", "no-NO": "no-NO", "pl-PL": "pl-PL", "pt-BR": "pt-BR", "ro": "ro",
    "ru-RU": "ru-RU", "sv-SE": "sv-SE", "th": "th", "tr-TR": "tr-TR", "uk": "uk",
    "ur": "ur", "vi": "vi", "zh-CN": "zh-CN",
}
LIMITS = {"appName": 64, "briefInfo": 80, "appDesc": 8000}


def txt(p):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def listing():
    out, problems = [], []
    for play, agc in sorted(LANG.items()):
        d = os.path.join(META, play)
        if not os.path.isdir(d):
            problems.append("%s: klasör yok" % play)
            continue
        item = {
            "lang": agc,
            "appName": txt(os.path.join(d, "title.txt")),
            "briefInfo": txt(os.path.join(d, "short_description.txt")),
            "appDesc": txt(os.path.join(d, "full_description.txt")),
        }
        for k, lim in LIMITS.items():
            if not item[k]:
                problems.append("%s: %s boş" % (play, k))
            elif len(item[k]) > lim:
                problems.append("%s: %s %d > %d karakter" % (play, k, len(item[k]), lim))
        out.append(item)
    return out, problems


def req(method, url, token=None, client_id=None, body=None, headers=None, raw=None):
    h = dict(headers or {})
    data = raw
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        h["Content-Type"] = "application/json"
    if token:
        h["Authorization"] = "Bearer " + token
        h["client_id"] = client_id
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(r, timeout=600) as resp:
                t = resp.read().decode("utf-8") or "{}"
                return json.loads(t) if t.lstrip().startswith("{") else {"raw": t}
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:500]
            if e.code >= 500 and attempt < 2:
                time.sleep(10)
                continue
            sys.exit("%s %s -> HTTP %d: %s" % (method, url.split("?")[0], e.code, msg))
        except urllib.error.URLError:
            if attempt < 2:
                time.sleep(10)
                continue
            raise


def ok(resp, what):
    code = (resp.get("ret") or {}).get("code", 0)
    if code != 0:
        sys.exit("%s başarısız: %s" % (what, json.dumps(resp.get("ret"), ensure_ascii=False)))
    return resp


def upload(token, cid, app_id, path):
    name = os.path.basename(path)
    size = os.path.getsize(path)
    suffix = name.rsplit(".", 1)[-1]
    q = urllib.parse.urlencode({"appId": app_id, "fileName": name, "contentLength": size, "suffix": suffix})
    r = req("GET", "%s/publish/v2/upload-url/for-obs?%s" % (API, q), token, cid)
    info = r.get("urlInfo")
    if (r.get("ret") or {}).get("code", 0) == 0 and info:
        with open(path, "rb") as f:
            req(info.get("method", "PUT"), info["url"], headers=info.get("headers") or {}, raw=f.read())
        dest = info["objectId"]
    else:
        # Eski yöntem (çok parçalı form): yeni uç nokta yoksa.
        q = urllib.parse.urlencode({"appId": app_id, "suffix": suffix})
        r = ok(req("GET", "%s/publish/v2/upload-url?%s" % (API, q), token, cid), "yükleme adresi")
        boundary = "----gs100%d" % int(time.time())
        parts = []
        for k, v in (("authCode", r["authCode"]), ("fileCount", "1"), ("parseType", "1")):
            parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, k, v)).encode())
        with open(path, "rb") as f:
            parts.append(('--%s\r\nContent-Disposition: form-data; name="file"; filename="%s"\r\n'
                          'Content-Type: application/octet-stream\r\n\r\n' % (boundary, name)).encode() + f.read() + b"\r\n")
        parts.append(("--%s--\r\n" % boundary).encode())
        res = req("POST", r["uploadUrl"], headers={"Content-Type": "multipart/form-data; boundary=" + boundary,
                                                   "Accept": "application/json"}, raw=b"".join(parts))
        fi = res["result"]["UploadFileRsp"]["fileInfoList"][0]
        dest = fi.get("fileDestUlr") or fi.get("fileDestUrl")
    body = {"fileType": 5, "files": [{"fileName": name, "fileDestUrl": dest, "size": str(size)}]}
    ok(req("PUT", "%s/publish/v2/app-file-info?appId=%s" % (API, app_id), token, cid, body=body), "paket bilgisi")
    print("yüklendi:", name, size, "bayt")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--file")
    ap.add_argument("--listing", action="store_true")
    ap.add_argument("--submit", action="store_true")
    a = ap.parse_args()

    items, problems = listing()
    os.makedirs("store/appgallery", exist_ok=True)
    with open("store/appgallery/listing.json", "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    if problems:
        sys.exit("AppGallery metinleri: " + "; ".join(problems))
    print("AppGallery metinleri: %d dil hazır (store/appgallery/listing.json)" % len(items))
    if a.check:
        return

    cid = os.environ.get("HUAWEI_CLIENT_ID", "")
    secret = os.environ.get("HUAWEI_CLIENT_SECRET", "")
    app_id = os.environ.get("HUAWEI_APP_ID", "")
    if not (cid and secret and app_id):
        print("::notice::HUAWEI_CLIENT_ID / HUAWEI_CLIENT_SECRET / HUAWEI_APP_ID tanımlı değil: AppGallery yüklemesi atlandı.")
        return
    tok = req("POST", "%s/oauth2/v1/token" % API, body={"grant_type": "client_credentials",
                                                          "client_id": cid, "client_secret": secret})
    token = tok.get("access_token")
    if not token:
        sys.exit("AppGallery belirteci alınamadı (istemci kimliği/sırrı yanlış olabilir)")
    if a.listing:
        for it in items:
            body = {k: it[k] for k in ("lang", "appName", "briefInfo", "appDesc")}
            ok(req("PUT", "%s/publish/v2/app-language-info?appId=%s" % (API, app_id), token, cid, body=body),
               "metin " + it["lang"])
        print("mağaza metinleri güncellendi: %d dil" % len(items))
    if a.file:
        upload(token, cid, app_id, a.file)
    if a.submit:
        ok(req("POST", "%s/publish/v2/app-submit?appId=%s" % (API, app_id), token, cid), "incelemeye gönderme")
        print("incelemeye gönderildi")


if __name__ == "__main__":
    main()
