// Minimal purchase verification endpoint (Node.js 20, Express or Cloud Functions).
// POST { platform: "android"|"ios", productId, purchaseToken | transactionId }
// -> { valid: boolean, consumed?: boolean, refunded?: boolean }
const { google } = require('googleapis');

const PACKAGE = 'com.gamestudio100.merkez_zihin_antrenmani';

async function verifyAndroid(productId, token) {
  const auth = new google.auth.GoogleAuth({ scopes: ['https://www.googleapis.com/auth/androidpublisher'] });
  const api = google.androidpublisher({ version: 'v3', auth });
  const r = await api.purchases.products.get({ packageName: PACKAGE, productId, token });
  // purchaseState: 0 purchased, 1 canceled, 2 pending
  return { valid: r.data.purchaseState === 0, refunded: r.data.purchaseState === 1 };
}

async function verifyIos(transactionId) {
  // Use Apple's App Store Server API (GET /inApps/v1/transactions/{transactionId})
  // signed with the In-App Purchase key (ES256 JWT). Library suggestion:
  // @apple/app-store-server-library
  const { AppStoreServerAPIClient, Environment } = require('@apple/app-store-server-library');
  const client = new AppStoreServerAPIClient(
    process.env.APPLE_IAP_KEY, process.env.APPLE_KEY_ID, process.env.APPLE_ISSUER_ID,
    PACKAGE, Environment.PRODUCTION);
  const info = await client.getTransactionInfo(transactionId);
  return { valid: !!info.signedTransactionInfo };
}

exports.verifyPurchase = async (req, res) => {
  try {
    const { platform, productId, purchaseToken, transactionId } = req.body || {};
    const result = platform === 'ios' ? await verifyIos(transactionId) : await verifyAndroid(productId, purchaseToken);
    res.json(result);
  } catch (e) {
    res.status(400).json({ valid: false, error: String(e.message || e) });
  }
};
