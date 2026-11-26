// Satın alma doğrulama uç noktası (Node.js 20; Express ya da Cloud Functions HTTP).
// İstemci (studio_core purchases_mobile.dart) yalnızca PURCHASE_VERIFY_URL
// tanımlıysa buraya sorar ve yalnızca { valid: true } yanıtında ödülü verir;
// doğrulanmayan satın alma mağazada onaylanmaz (Google Play 3 günde iade eder).
//
// POST { platform: "android"|"ios", productId, purchaseToken, transactionId }
// -> { valid: boolean }
//
// Gerekenler:
//  - Android: Play Console > API erişimi ile yetkilendirilmiş hizmet hesabı
//    (GOOGLE_APPLICATION_CREDENTIALS ya da Cloud Functions varsayılan hesabı).
//  - iOS: App Store Connect In-App Purchase anahtarı: APPLE_IAP_KEY (p8 içeriği),
//    APPLE_KEY_ID, APPLE_ISSUER_ID; APPLE_ENV=SANDBOX ile test.
// Not: Bu uç nokta herkese açıktır; yanıt yalnızca "geçerli mi" bilgisidir.
// Hata ayrıntısı istemciye gönderilmez.
const { google } = require('googleapis');

const PACKAGE = 'com.gamestudio100.merkez_zihin_antrenmani';
const PRODUCTS = new Set((process.env.PRODUCT_IDS || '').split(',').map((s) => s.trim()).filter(Boolean));

async function verifyAndroid(productId, token) {
  const auth = new google.auth.GoogleAuth({ scopes: ['https://www.googleapis.com/auth/androidpublisher'] });
  const api = google.androidpublisher({ version: 'v3', auth });
  const r = await api.purchases.products.get({ packageName: PACKAGE, productId, token });
  // purchaseState: 0 satın alındı, 1 iptal/iade, 2 beklemede
  return r.data.purchaseState === 0;
}

function decodeJws(jws) {
  const part = String(jws || '').split('.')[1] || '';
  return JSON.parse(Buffer.from(part, 'base64url').toString('utf8'));
}

async function verifyIos(productId, transactionId) {
  // App Store Server API yanıtı Apple'dan TLS ile, kendi anahtarımızla imzalı
  // istekle gelir; yine de işlemin bu uygulamaya ve bu ürüne ait olduğu,
  // iade edilmediği denetlenir.
  const { AppStoreServerAPIClient, Environment } = require('@apple/app-store-server-library');
  const env = process.env.APPLE_ENV === 'SANDBOX' ? Environment.SANDBOX : Environment.PRODUCTION;
  const client = new AppStoreServerAPIClient(
    process.env.APPLE_IAP_KEY, process.env.APPLE_KEY_ID, process.env.APPLE_ISSUER_ID, PACKAGE, env);
  const info = await client.getTransactionInfo(transactionId);
  const tx = decodeJws(info.signedTransactionInfo);
  return tx.bundleId === PACKAGE && tx.productId === productId && !tx.revocationDate;
}

exports.verifyPurchase = async (req, res) => {
  try {
    if (req.method !== 'POST') return res.status(405).json({ valid: false });
    const { platform, productId, purchaseToken, transactionId } = req.body || {};
    if (typeof productId !== 'string' || productId.length > 100 || (PRODUCTS.size && !PRODUCTS.has(productId))) {
      return res.status(400).json({ valid: false });
    }
    let valid = false;
    if (platform === 'ios' && typeof transactionId === 'string' && /^[0-9]{1,32}$/.test(transactionId)) {
      valid = await verifyIos(productId, transactionId);
    } else if (platform === 'android' && typeof purchaseToken === 'string' && purchaseToken.length < 4096) {
      valid = await verifyAndroid(productId, purchaseToken);
    }
    res.json({ valid });
  } catch (e) {
    console.error('verifyPurchase', e);
    res.status(400).json({ valid: false });
  }
};
