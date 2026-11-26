import 'package:flutter_test/flutter_test.dart';
import 'package:merkez_zihin_antrenmani/approved_style.dart';
import 'package:merkez_zihin_antrenmani/main.dart';
import 'package:studio_core/app/approved_hub.dart';
import 'package:studio_core/app/global_daily_ui.dart';

void main() {
  test('merkezde oyunlar benzersiz kimlikle yer alıyor', () {
    final ids = hubConfig.games.map((g) => g.gameId).toList();
    expect(ids, [
      'oyun-gunluk-beyin-egzersizi-programi',
      'oyun-hafiza-dizisi',
      'oyun-gorsel-hafiza-izgarasi',
      'oyun-n-geri',
      'oyun-yuz-ve-isim',
      'oyun-rakam-dizisi',
      'oyun-kelime-hafizasi',
      'oyun-stroop-testi',
      'oyun-schulte-tablosu',
      'oyun-tepki-ve-odak',
      'oyun-hizli-hesap',
      'oyun-cift-gorev',
      'oyun-gorsel-arama',
      'oyun-oruntu-tamamlama',
      'oyun-uzamsal-dondurme',
      'oyun-kestirme-ustasi',
      'oyun-iz-surme',
      'oyun-ok-yonu',
    ]);
    final all = hubConfig.allGames.map((g) => g.gameId).toList();
    expect(all.length, ids.length + 0);
    expect(all.toSet().length, all.length);
    expect(ids.toSet().length, ids.length);
    for (final g in hubConfig.allGames) {
      expect(g.rules.gameId, g.gameId, reason: 'kayıt öneki oyun kimliğiyle aynı olmalı');
    }
    expect(hubConfig.title.length, 33);
    expect(hubConfig.tagline.length, 33);
  });

  test('her oyun ve grup bir bölüm başlığı altında', () {
    final ids = {for (final s in hubConfig.sections) ...s.ids};
    for (final g in hubConfig.games) {
      expect(ids.contains(g.gameId), isTrue, reason: g.gameId);
    }
    for (final s in hubConfig.sections) {
      expect(s.title.length, 33);
    }
  });

  test('Günün Bulmacası: katılan oyunlar herkese aynı günlük bölümü verir; Aile Turnuvası menüde', () {
    expect(approvedStyle.blocks, contains(ApprovedBlock.globalDaily));
    final daily = GlobalDailyHubPage.eligible(hubConfig.allGames);
    expect(daily, isNotEmpty);
    for (final g in daily) {
      final a = g.rules.globalDailySpec('2026-11-26');
      expect(a.seed, g.rules.globalDailySpec('2026-11-26').seed, reason: g.gameId);
      expect(a.seed, isNot(g.rules.globalDailySpec('2026-11-27').seed), reason: g.gameId);
    }
    // Turnuva menüsü: merkezin bütün oyunları seçilebilir.
    expect(hubConfig.allGames.length, greaterThanOrEqualTo(2));
  });
}
