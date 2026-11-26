// Ekran boyutları: merkezin ana ekranları ve her oyunun açılış ekranı (oyun
// ana sayfası + ilk bölüm) küçük telefondan yatay tablete kadar, büyük yazı
// ve sağdan sola dilde taşmadan, metin kesilmeden, düğmeler erişilebilir
// biçimde açılır. CI'da ayrı işte çalışır (etiket: boyut).
@Tags(['boyut'])
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:merkez_zihin_antrenmani/main.dart' as hub;
import 'package:merkez_zihin_antrenmani/approved_style.dart' as look;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:studio_core/app/app_state.dart';
import 'package:studio_core/app/approved_hub.dart' show ApprovedHubShell, ApprovedLook;
import 'package:studio_core/app/bootstrap.dart';
import 'package:studio_core/app/hub.dart';
import 'package:studio_core/app/screens/home.dart';
import 'package:studio_core/app/screens/play.dart';
import 'package:studio_core/app/services/ads.dart';
import 'package:studio_core/app/services/audio.dart';
import 'package:studio_core/app/services/prefs_backend.dart';
import 'package:studio_core/app/services/purchases.dart';
import 'package:studio_core/app/studio_look.dart';
import 'package:studio_core/core/telemetry.dart';

import 'layout_check.dart';

final issues = LayoutIssues();

Future<HubServices> _services() async {
  SharedPreferences.setMockInitialValues({'hub.consent': 'granted', 'hub.guide.v1': '1'});
  final backend = await PrefsBackend.create();
  final s = HubServices(
    backend: backend,
    errors: ErrorJournal(backend),
    analytics: AnalyticsQueue(backend),
    emergency: EmergencyConfig(),
    perf: PerformanceMonitor(),
    ads: NoAdsService(),
    purchases: NoPurchaseService(),
    audio: AudioService(),
  );
  await s.loadShared();
  return s;
}

/// Oyunlarda telefonlar dikey kilitli (Adaptive.applyOrientationPolicy):
/// yatay yalnız kısa kenarı 600 ve üstü olan ekranlarda denenir.
const _gameScreens = kScreens;
bool _skip(Size s) => s.width > s.height && s.shortestSide < 600;

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    for (final ch in ['xyz.luan/audioplayers', 'xyz.luan/audioplayers.global']) {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(MethodChannel(ch), (call) async => null);
    }
  });
  tearDownAll(() => issues.printSummary('merkez_zihin_antrenmani'));

  testWidgets('merkez ana ekranları tüm boyutlarda', (tester) async {
    final s = (await tester.runAsync(_services))!;
    await sweep(tester, issues, 'merkez', skip: _skip, screens: _gameScreens,
        langScales: const [('tr', 1.0), ('tr', 1.3), ('ar', 1.3)], (lang) async {
      await tester.pumpWidget(fresh(MaterialApp(
        home: ApprovedHubShell(hub: hub.hubConfig, style: look.approvedStyle, services: s, lang: lang),
      )));
    });
    expect(issues.items.where((i) => i.startsWith('SORUN|merkez|')).toList(), isEmpty);
  }, timeout: const Timeout(Duration(minutes: 10)));

  for (final g in hub.hubConfig.allGames) {
    testWidgets('açılış ekranları tüm boyutlarda: ${g.gameId}', (tester) async {
      // Her tarama kendi durumunu kullanır (ağaç kaldırılınca durum kapanır).
      Future<AppState> newState() async {
        final s = (await tester.runAsync(_services))!;
        final st = (await tester.runAsync(() => s.stateFor(g)))!;
        st.startup = null;
        st.save.ageGateDone = true;
        if (st.save.adConsent.isEmpty) st.save.adConsent = 'denied';
        st.save.stats['tutorial_seen'] = 1;
        return st;
      }

      Widget app(AppState st) => ProviderScope(
            overrides: [appStateProvider.overrideWith((ref) => st)],
            child: fresh(StudioLookScope(look: look.approvedStyle.look, child: GameApp(state: st))),
          );
      // Oyunun ana sayfası (ortak ekran; uzun adlar için küçük ekranlar yeter).
      final st1 = await newState();
      await sweep(tester, issues, '${g.gameId}/ana', skip: _skip,
          screens: [kScreens[0], kScreens[5], kScreens[8]],
          langScales: const [('tr', 1.3), ('ar', 1.3)], (lang) async {
        st1.save.language = lang;
        await tester.pumpWidget(app(st1));
      });
      // İlk bölüm: motorun oyun ekranı.
      final st2 = await newState();
      await sweep(tester, issues, '${g.gameId}/oyun', skip: _skip, screens: _gameScreens,
          langScales: const [('tr', 1.3), ('ar', 1.3)], settleMs: 600, (lang) async {
        st2.save.language = lang;
        await tester.pumpWidget(app(st2));
        await tester.pump(const Duration(milliseconds: 100));
        final home = find.byType(HomeScreen);
        if (home.evaluate().isEmpty) return;
        Navigator.of(tester.element(home), rootNavigator: true)
            .push(MaterialPageRoute<void>(builder: (_) => PlayScreen(spec: st2.session.planner.spec(1))));
        for (var i = 0; i < 6; i++) {
          await tester.pump(const Duration(milliseconds: 100));
        }
      });
      expect(issues.items.where((i) => i.startsWith('SORUN|${g.gameId}/')).toList(), isEmpty);
    }, timeout: const Timeout(Duration(minutes: 10)));
  }
}
