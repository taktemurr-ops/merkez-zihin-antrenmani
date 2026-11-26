# Zihin Antrenmanı · Brain Training (merkez-zihin-antrenmani)

Zihin ailesinin **merkez uygulaması**: 18 kısa egzersizi (hafıza, dikkat ve hız, mantık ve uzam) tek mağaza uygulamasında toplar. Her egzersiz kendi deposundadır; ortak motor [zihin-motoru](https://github.com/taktemurr-ops/zihin-motoru), ortak çekirdek [studio-core](https://github.com/taktemurr-ops/studio-core). Egzersizler eğlence ve alıştırma içindir; tıbbi iddia taşımaz.

## Günün Bulmacası (küresel günlük meydan okuma)

Ana sayfadaki kart ve menüdeki **Günün Bulmacası**: katılan her oyunda dünyadaki herkes aynı UTC gününde aynı bulmacayı çözer (tohum yalnızca oyun + gün; motor bölümü verir, `GameRules.globalDailySpec`). Günün ilk çözümü sıralamaya girer (süre/hamle ya da puan), seri ve en iyi seri tutulur, sonuç bulmacayı ele vermeyen emoji izli metinle paylaşılır. Çevrimdışı çözülen sonuç cihazda bekler, bağlantı gelince gönderilir (Firestore `daily/{tablo}/results/{uid}`, kurallar ve emülatör testleri studio-core'da).

## Aile Turnuvası

Menüdeki **Aile Turnuvası** (Parti ve Aile merkezinde ana sayfada da): aynı cihazda 2–8 kişi, merkezin oyunlarından seçilenlerle 1–5 tur. Sırayla oynanan oyunlarda herkes aynı bölümü oynar (1.: 3, 2.: 2, 3.: 1 puan); birlikte oynanan oyunlarda kalabalık aileler gruplara ayrılır. Puan tablosu, şampiyon töreni ve kaldığı yerden devam; çevrimiçi bağlantı, reklam ya da kişisel bilgi yok (takma adlar yalnızca cihazda).

| Egzersiz | Depo |
|---|---|
| Günlük Zihin Programı | [oyun-gunluk-beyin-egzersizi-programi](https://github.com/taktemurr-ops/oyun-gunluk-beyin-egzersizi-programi) |
| Renk Dizisi | [oyun-hafiza-dizisi](https://github.com/taktemurr-ops/oyun-hafiza-dizisi) |
| Görsel Hafıza | [oyun-gorsel-hafiza-izgarasi](https://github.com/taktemurr-ops/oyun-gorsel-hafiza-izgarasi) |
| Geri Hafıza | [oyun-n-geri](https://github.com/taktemurr-ops/oyun-n-geri) |
| Yüz ve İsim | [oyun-yuz-ve-isim](https://github.com/taktemurr-ops/oyun-yuz-ve-isim) |
| Rakam Dizisi | [oyun-rakam-dizisi](https://github.com/taktemurr-ops/oyun-rakam-dizisi) |
| Kelime Hafızası | [oyun-kelime-hafizasi](https://github.com/taktemurr-ops/oyun-kelime-hafizasi) |
| Renk mi Kelime mi | [oyun-stroop-testi](https://github.com/taktemurr-ops/oyun-stroop-testi) |
| Sayı Tablosu | [oyun-schulte-tablosu](https://github.com/taktemurr-ops/oyun-schulte-tablosu) |
| Tepki ve Odak | [oyun-tepki-ve-odak](https://github.com/taktemurr-ops/oyun-tepki-ve-odak) |
| Hızlı Hesap | [oyun-hizli-hesap](https://github.com/taktemurr-ops/oyun-hizli-hesap) |
| Çift Görev | [oyun-cift-gorev](https://github.com/taktemurr-ops/oyun-cift-gorev) |
| Görsel Arama | [oyun-gorsel-arama](https://github.com/taktemurr-ops/oyun-gorsel-arama) |
| Örüntü Tamamla | [oyun-oruntu-tamamlama](https://github.com/taktemurr-ops/oyun-oruntu-tamamlama) |
| Uzamsal Döndürme | [oyun-uzamsal-dondurme](https://github.com/taktemurr-ops/oyun-uzamsal-dondurme) |
| Kestirme Ustası | [oyun-kestirme-ustasi](https://github.com/taktemurr-ops/oyun-kestirme-ustasi) |
| İz Sürme | [oyun-iz-surme](https://github.com/taktemurr-ops/oyun-iz-surme) |
| Ok Yönü | [oyun-ok-yonu](https://github.com/taktemurr-ops/oyun-ok-yonu) |

Test APK: https://github.com/taktemurr-ops/merkez-zihin-antrenmani/releases/download/test/merkez-zihin-antrenmani.apk
