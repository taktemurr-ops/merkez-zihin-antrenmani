// Arayüz incelemesi: merkez uygulamasını baştan açar; izin, ilk açılış
// rehberi, ana liste, çeşit grupları ve her oyunun ilk bölümünü (öğretici
// pencere ve oyun ekranı) sırayla açıp ekran görüntüsü alır. Yalnızca
// ui-review iş akışında çalışır; görüntüler /tmp/review altına yazılır.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:merkez_zihin_antrenmani/main.dart' as hub;
import 'package:studio_core/app/screens/play.dart';
import 'package:studio_core/core/strings.dart';

const _lang = String.fromEnvironment('LANG_UI', defaultValue: 'tr');

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('arayüz incelemesi', (tester) async {
    tester.platformDispatcher.localeTestValue = const Locale(_lang);
    tester.platformDispatcher.localesTestValue = const [Locale(_lang)];
    tester.view.physicalSize = const Size(1080, 2280);
    tester.view.devicePixelRatio = 2.75;
    final lang = Strings.pickLanguage(ui.PlatformDispatcher.instance.locale.languageCode);
    final t = Strings(lang);
    final log = <String>['dil: $lang'];
    var n = 0;

    Future<void> wait([int ms = 1200]) async {
      for (var i = 0; i < ms ~/ 100; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
    }

    Future<void> shot(String name) async {
      await wait(800);
      n++;
      final file = '${n.toString().padLeft(2, '0')}_$name';
      try {
        final rv = tester.binding.renderViews.first;
        final layer = rv.debugLayer! as OffsetLayer;
        final size = rv.flutterView.physicalSize;
        await tester.runAsync(() async {
          final img = await layer.toImage(Offset.zero & size);
          final data = await img.toByteData(format: ui.ImageByteFormat.png);
          img.dispose();
          final f = File('${Directory.systemTemp.path}/review/$file.png');
          f.createSync(recursive: true);
          f.writeAsBytesSync(data!.buffer.asUint8List());
        });
        log.add('OK   $file');
      } catch (e) {
        log.add('SHOT $file: $e');
      }
    }

    Future<void> step(String name, Future<void> Function() f) async {
      try {
        await f();
      } catch (e) {
        log.add('FAIL $name: ${e.toString().split('\n').first}');
      }
    }

    Future<void> tapText(String text) async {
      final f = find.text(text).last;
      await tester.ensureVisible(f);
      await tester.pump();
      await tester.tap(f);
      await wait();
    }

    Future<void> scrollTap(String text) async {
      final f = find.text(text);
      if (f.evaluate().isEmpty) {
        // Listenin başına dön, sonra aşağı doğru ara.
        for (var i = 0; i < 6; i++) {
          await tester.drag(find.byType(Scrollable).first, const Offset(0, 3000));
          await tester.pump(const Duration(milliseconds: 200));
        }
        await tester.scrollUntilVisible(f, 300, scrollable: find.byType(Scrollable).first, maxScrolls: 80);
      }
      await tapText(text);
    }


    Future<void> home() async {
      tester.state<NavigatorState>(find.byType(Navigator).first).popUntil((r) => r.isFirst);
      await wait();
    }

    hub.main();
    await wait(4000);
    await shot('izin');
    await step('izin kabul', () => tapText(t.t('accept_all')));
    await wait(2000);
    await shot('ilk_acilis_rehberi');
    await step('rehberi kapat', () => tapText(t.t('hub_browse')));
    await shot('ana_liste');
    for (final g in hub.hubConfig.groups) {
      await step('grup ${g.id}', () async {
        await scrollTap(hub.hubConfig.localized(g.title, lang));
        await shot('grup_${g.id}');
        await home();
      });
    }

    for (final g in hub.hubConfig.games) {
      final id = g.gameId.replaceFirst('oyun-', '');
      await step('$id ac', () => scrollTap(hub.hubConfig.localized(g.title, lang)));
      await wait(2500);
      await step('$id ana sekme', () async {
        await tester.tap(find.byIcon(Icons.home).last);
        await wait();
      });
      await step('$id oyna', () async {
        final play = find.text(t.t('play'));
        await tapText(play.evaluate().isNotEmpty ? t.t('play') : t.t('resume'));
        await wait(2500);
      });
      await shot('${id}_ogretici');
      await step('$id ogretici kapat', () => tapText(t.t('got_it')));
      await shot('${id}_oyun');
      await step('$id dokun', () async {
        final r = tester.getRect(find.byType(PlayScreen));
        await tester.tapAt(r.center + Offset(0, r.height * 0.08));
        await wait(1500);
      });
      await shot('${id}_dokunus');
      await home();
    }

    final out = File('${Directory.systemTemp.path}/review/log.txt');
    out.createSync(recursive: true);
    out.writeAsStringSync(log.join('\n'));
    // ignore: avoid_print
    print(log.join('\n'));
  }, timeout: const Timeout(Duration(minutes: 30)));
}
