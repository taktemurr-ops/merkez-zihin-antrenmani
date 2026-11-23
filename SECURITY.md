# Güvenlik · Security — Brain Training

## Bildirim / Reporting
Bir güvenlik açığı bulursanız lütfen herkese açık issue açmayın; depo sahibine
GitHub "Security → Report a vulnerability" üzerinden özel olarak bildirin.
Please report vulnerabilities privately via GitHub "Security → Report a vulnerability".

## Uygulanan önlemler / Measures in this repository

| Alan | Önlem |
|---|---|
| Oyuncu kaydı | Her kayıt HMAC-SHA256 ile imzalanır (`lib/core/integrity.dart`); elle düzenlenen ya da bozulan kayıt reddedilir, son geçerli yedeğe dönülür. Dışa aktarılan yedek de imzalıdır; başka oyunun ya da imzasız yedek içe alınmaz. |
| Satın alma | Mağaza (Google Play / App Store) doğrulaması, tekrar ve iade koruması; sunucu doğrulaması için `server/purchase_verifier` ve `docs/PURCHASE_VERIFICATION.md`. |
| Saat hilesi | Saat geri alınınca günlük ödüller yeniden açılmaz (`lib/core/clock.dart`). |
| Ağ | Android: yalnızca HTTPS (`network_security_config`, cleartext kapalı). iOS: App Transport Security açık. Web: `strict-origin-when-cross-origin` referrer politikası. |
| Derleme | Android ve iOS sürüm derlemeleri `--obfuscate --split-debug-info` ile; semboller CI'da gizli artifact olarak saklanır. |
| Gizli bilgiler | İmza anahtarları, keystore, servis hesapları depoya konmaz (`.gitignore`); CI ilk adımda `tool/check_secrets.py` ile tarar. Anahtarlar yalnızca GitHub Secrets'ta tutulur (`docs/RELEASE.md`). |
| CI | Tüm iş akışları salt-okunur `GITHUB_TOKEN` ile çalışır (`permissions: contents: read`). |
| Bağımlılıklar | Dependabot haftalık pub ve GitHub Actions güncellemeleri (`.github/dependabot.yml`). |
| Gizlilik / çocuk | Yaş kapısı, UMP/GDPR rızası, 13 yaş altına kişiselleştirilmemiş reklam, analitik rızaya bağlı (`PRIVACY.md`). |
| Kriz durumu | `assets/config/emergency.json` ile reklam/satın alma/analitik uzaktan kapatılabilir; art arda çökmede güvenli mod. |

## Sınırlar / Limits
Uygulamanın içindeki bir anahtar kararlı bir saldırganı tamamen durduramaz; kayıt imzası
çevrimdışı oyun için caydırıcıdır. Gerçek para değeri taşıyan her şey mağaza/sunucu
tarafında doğrulanmalıdır.

## Web barındırma önerisi / Web hosting
`build/web` yayınlanırken sunucuda şu başlıkları ekleyin:
`Strict-Transport-Security`, `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY` (veya CSP `frame-ancestors 'none'`), `Referrer-Policy`.
