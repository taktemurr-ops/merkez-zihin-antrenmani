# Satın alma doğrulama (sunucu tarafı)

Uygulama satın almaları cihazda `PurchaseLedger` ile işler (tekrar koruması, geri yükleme,
iade, bekleyen ödeme). Mağaza imzası boş olmayan satın alma "doğrulanmış" sayılır.

Yayında sahte satın almaları tamamen engellemek için `server/purchase_verifier/` altındaki
örnek fonksiyon kullanılabilir (Firebase Cloud Functions / herhangi bir Node.js sunucusu):

1. Google Play: Play Console → API erişimi → servis hesabı oluştur, JSON anahtarını sunucuya
   ortam değişkeni olarak ver (`GOOGLE_APPLICATION_CREDENTIALS`).
2. Apple: App Store Connect → Kullanıcılar ve Erişim → Entegrasyonlar → In-App Purchase anahtarı.
3. Fonksiyonu yayınla, adresini `lib/app/services/purchases_mobile.dart` içindeki `_verify`
   yerine çağır (cevap `{"valid": true}` ise ödülü ver).

Sunucu yokken oyun yine çalışır; sadece doğrulama cihazda yapılır.
