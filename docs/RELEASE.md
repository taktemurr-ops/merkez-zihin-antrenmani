# Yayın kontrol listesi · Zihin Antrenmanı

Kod tarafı hazır. Aşağıdakiler hesap/anahtar gerektirdiği için **sahibi tarafından** yapılmalıdır.

## 1. Kimlikler
- Paket / Bundle ID: `com.gamestudio100.merkez_zihin_antrenmani`
- Uygulama adı: Zihin Antrenmanı (TR) / Brain Training (EN)

## 2. AdMob
1. AdMob'da bu oyun için Android ve iOS uygulaması oluştur.
2. Bir geçiş (interstitial) ve bir ödüllü (rewarded) reklam birimi oluştur.
3. GitHub → Settings → Secrets: `ADMOB_APP_ID_ANDROID`, `ADMOB_APP_ID_IOS`, `ADMOB_ANDROID_INTERSTITIAL`, `ADMOB_ANDROID_REWARDED` ekle. CI bunları derlemeye kendisi yazar; tanımlı değilse test reklamları kullanılır. Koda dokunmak gerekmez.
5. AdMob → Gizlilik ve mesajlaşma: GDPR mesajını yayınla (uygulama UMP formunu otomatik gösterir).

## 3. Mağaza ürünleri (Play Console + App Store Connect)
| Ürün kimliği | Tür |
|---|---|
| `remove_ads` | Tüketilmeyen (non-consumable) |
| `premium_pack` | Tüketilmeyen |
| `coins_small` | Tüketilen (consumable) |
| `coins_large` | Tüketilen |
| `hint_pack` | Tüketilen |
| `starter_pack` | Tüketilen |

Üretimde satın alma doğrulaması için bir sunucu (Google Play Developer API / App Store Server API) önerilir; kanca `lib/app/services/purchases_mobile.dart` → `_verify`.

## 4. İmzalama
- Android: yükleme anahtarı (upload keystore) oluştur ve GitHub → Settings → Secrets'a ekle: `ANDROID_KEYSTORE_BASE64` (jks dosyasının base64 hâli), `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`. CI tanımlıysa sürümü bu anahtarla imzalar; değilse test anahtarıyla.
- iOS: Apple Developer hesabı, sertifika ve provisioning profile; `fastlane/Fastfile` → `ios beta`.

## 5. Mağaza sayfası
- Metinler: `fastlane/metadata/` (TR + EN)
- Görseller: CI artefaktı `store-graphics` (ikon 512, feature graphic 1024×500, ekran çerçeveleri). Gerçek oyun ekran görüntülerini de cihazdan/emülatörden ekle.
- Gizlilik politikası: `PRIVACY.md` içeriğini bir web adresinde yayınla ve `GameConfig.privacyUrl` alanına yaz.
- Yaş sınıflandırması: IARC (Play) / App Store yaş anketi. Oyunda 16 yaş altı için kişiselleştirilmiş reklam ve analitik kapalıdır.

## 6. İsteğe bağlı: Firebase Crashlytics / Analytics
Kod, analitik ve hata kayıtlarını cihazda kuyrukta tutar (`AnalyticsSink`). Firebase projesi açılınca
`google-services.json` / `GoogleService-Info.plist` eklenip `AnalyticsSink` için Firebase adaptörü bağlanır.

## 7. Son test
- [ ] CI yeşil (analiz, testler, APK/AAB, Web)
- [ ] Haftalık dayanıklılık testi yeşil (10.000 bölüm + 730 gün simülasyon)
- [ ] Gerçek Android cihazda: reklam, satın alma (test hesabı), uçak modu, uygulamayı öldürüp devam
- [ ] Gerçek iPhone'da aynı testler (TestFlight)
- [ ] Tablet testleri: Android tablet (yatay + dikey, çoklu pencere), katlanabilir (açık/kapalı), iPad (Split View / Stage Manager)
- [ ] Web: Chrome, Safari (iOS/macOS), Firefox; dar ve geniş pencere; sayfayı yenileyince kayıt korunuyor
- [ ] Güvenlik: `tool/check_secrets.py` temiz, sürüm derlemeleri obfuscate, `build/symbols` arşivlendi, Dependabot uyarıları kapalı
