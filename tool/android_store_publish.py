#!/usr/bin/env python3
"""Galaxy Store ve Amazon Appstore'a yükleme (bkz. .github/workflows/android-stores.yml).

  python tool/android_store_publish.py samsung --file app.apk [--submit]
      Galaxy Store Developer API (Content Publish API). Ortam:
      SAMSUNG_SERVICE_ACCOUNT_ID, SAMSUNG_PRIVATE_KEY (PEM, RS256),
      SAMSUNG_CONTENT_ID (uygulamanın Seller Portal içerik kimliği).
      Akış: erişim belirteci (JWT) -> yükleme oturumu -> dosya yükleme ->
      (satıştaysa) güncelleme oluştur -> ikili ekle -> isteğe bağlı inceleme.

  python tool/android_store_publish.py amazon --file a.apk [--file b.apk] [--submit]
      Amazon App Submission API. Ortam: AMAZON_CLIENT_ID,
      AMAZON_CLIENT_SECRET, AMAZON_APP_ID. Akış: belirteç -> açık düzenleme
      (yoksa oluştur) -> APK'ları değiştir/yükle -> doğrula -> isteğe bağlı
      gönder (commit).

Değişkenler yoksa temiz biçimde atlar (çıkış 0). Gizli değerler yazdırılmaz.
Kaynaklar:
  https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/create-an-access-token.html
  https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/content-publish-api/user-guide-submit-an-update.html
  https://developer.amazon.com/docs/app-submission-api/flows.html
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

UA = "studio-store-publish/1.0"


def http(method, url, headers=None, body=None, raw=False):
    req = urllib.request.Request(url, method=method, data=body, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = r.read()
            return r.status, dict(r.headers), (data if raw else (json.loads(data) if data.strip() else {}))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")[:800]
        sys.exit("%s %s -> HTTP %s: %s" % (method, url.split("?")[0], e.code, text))


def multipart(fields, files):
    b = "----studio" + uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b, k, v)).encode())
    for k, path in files.items():
        with open(path, "rb") as f:
            data = f.read()
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
                    "Content-Type: application/octet-stream\r\n\r\n" % (b, k, os.path.basename(path))).encode())
        out.append(data + b"\r\n")
    out.append(("--%s--\r\n" % b).encode())
    return b"".join(out), "multipart/form-data; boundary=" + b


def need(*names):
    missing = [n for n in names if not os.environ.get(n, "").strip()]
    if missing:
        print("::notice::%s yok: yükleme atlandı." % " / ".join(missing))
        sys.exit(0)
    return [os.environ[n].strip() for n in names]


# ---- Galaxy Store -------------------------------------------------------------

SDEV = "https://devapi.samsungapps.com"


def samsung(files, submit):
    sa, key, content = need("SAMSUNG_SERVICE_ACCOUNT_ID", "SAMSUNG_PRIVATE_KEY", "SAMSUNG_CONTENT_ID")
    import jwt  # PyJWT[crypto] (iş akışı kurar)

    now = int(time.time())
    token_jwt = jwt.encode({"iss": sa, "scopes": ["publishing"], "iat": now, "exp": now + 1200},
                           key.replace("\\n", "\n"), algorithm="RS256")
    _, _, r = http("POST", SDEV + "/auth/accessToken",
                   {"Content-Type": "application/json", "Authorization": "Bearer " + token_jwt})
    token = ((r or {}).get("createdItem") or {}).get("accessToken")
    if not token:
        sys.exit("Galaxy Store erişim belirteci alınamadı")
    h = {"Authorization": "Bearer " + token, "service-account-id": sa}

    _, _, info = http("GET", SDEV + "/seller/contentInfo?contentId=" + urllib.parse.quote(content), h)
    item = info[0] if isinstance(info, list) and info else info
    status = (item or {}).get("contentStatus") or (item or {}).get("appStatus") or ""
    binaries = (item or {}).get("binaryList") or []
    base_seq = str(binaries[-1].get("binarySeq")) if binaries else ""
    print("Galaxy Store içerik durumu:", status or "?")
    if status.upper() in ("FOR_SALE", "SALE", "BETA_DEPLOYED"):
        # Satıştaki uygulama için güncelleme kaydı (REGISTRATION) açılır.
        http("POST", SDEV + "/seller/contentUpdate", {**h, "Content-Type": "application/json"},
             json.dumps({"contentId": content}).encode())

    for path in files:
        _, _, sess = http("POST", SDEV + "/seller/createUploadSessionId", h)
        sid = sess.get("sessionId")
        url = sess.get("url") or "https://seller.samsungapps.com/galaxyapi/fileUpload"
        body, ctype = multipart({"sessionId": sid}, {"file": path})
        _, _, up = http("POST", url, {**h, "Content-Type": ctype}, body)
        fkey = up.get("fileKey")
        if not fkey:
            sys.exit("Galaxy Store dosya yükleme başarısız: %s" % json.dumps(up)[:300])
        payload = {"contentId": content, "gms": "Y", "filekey": fkey}
        if base_seq:
            payload["binarySeqForDeviceInfo"] = base_seq  # cihaz ayarlarını kopyala
        _, _, add = http("POST", SDEV + "/seller/v2/content/binary", {**h, "Content-Type": "application/json"},
                         json.dumps(payload).encode())
        if str(add.get("resultCode")) not in ("0000", "0"):
            sys.exit("Galaxy Store ikili ekleme reddedildi: %s" % json.dumps(add)[:300])
        print("Galaxy Store: %s eklendi (binarySeq %s)" % (os.path.basename(path), (add.get("data") or {}).get("binarySeq")))

    if submit:
        http("POST", SDEV + "/seller/contentSubmit", {**h, "Content-Type": "application/json"},
             json.dumps({"contentId": content}).encode())
        print("Galaxy Store: incelemeye gönderildi")
    else:
        print("Galaxy Store: taslak hazır (Seller Portal'dan ya da --submit ile gönderin)")


# ---- Amazon Appstore ------------------------------------------------------------

ABASE = "https://developer.amazon.com/api/appstore/v1/applications/"


def amazon(files, submit):
    cid, secret, app = need("AMAZON_CLIENT_ID", "AMAZON_CLIENT_SECRET", "AMAZON_APP_ID")
    form = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": cid, "client_secret": secret,
                                   "scope": "appstore::apps:readwrite"}).encode()
    _, _, tok = http("POST", "https://api.amazon.com/auth/o2/token",
                     {"Content-Type": "application/x-www-form-urlencoded"}, form)
    h = {"Authorization": "Bearer " + tok["access_token"]}
    base = ABASE + urllib.parse.quote(app)

    _, _, edit = http("GET", base + "/edits", h)
    if not edit or not edit.get("id"):
        _, _, edit = http("POST", base + "/edits", h)
    eid = edit["id"]
    print("Amazon: düzenleme", eid)
    _, _, apks = http("GET", "%s/edits/%s/apks" % (base, eid), h)
    apks = apks if isinstance(apks, list) else []
    for i, path in enumerate(files):
        with open(path, "rb") as f:
            data = f.read()
        ah = {**h, "Content-Type": "application/vnd.android.package-archive"}
        if i < len(apks):
            aid = apks[i]["id"]
            _, hdr, _ = http("GET", "%s/edits/%s/apks/%s" % (base, eid, aid), h)
            etag = hdr.get("ETag") or hdr.get("Etag") or ""
            http("PUT", "%s/edits/%s/apks/%s/replace" % (base, eid, aid), {**ah, "If-Match": etag}, data)
            print("Amazon: APK değiştirildi:", os.path.basename(path))
        else:
            http("POST", "%s/edits/%s/apks/upload" % (base, eid), ah, data)
            print("Amazon: APK yüklendi:", os.path.basename(path))

    _, _, val = http("POST", "%s/edits/%s/validate" % (base, eid), h)
    print("Amazon: doğrulama", json.dumps(val)[:300])
    if submit:
        _, hdr, _ = http("GET", "%s/edits/%s" % (base, eid), h)
        etag = hdr.get("ETag") or hdr.get("Etag") or ""
        http("POST", "%s/edits/%s/commit" % (base, eid), {**h, "If-Match": etag})
        print("Amazon: incelemeye gönderildi (commit)")
    else:
        print("Amazon: düzenleme açık bırakıldı (Developer Console'dan ya da --submit ile gönderin)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("store", choices=["samsung", "amazon"])
    ap.add_argument("--file", action="append", required=True)
    ap.add_argument("--submit", action="store_true")
    a = ap.parse_args()
    for p in a.file:
        if not os.path.isfile(p):
            sys.exit("dosya yok: %s" % p)
    (samsung if a.store == "samsung" else amazon)(a.file, a.submit)


if __name__ == "__main__":
    main()
