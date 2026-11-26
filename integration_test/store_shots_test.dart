// Mağaza görselleri: gerçek oyun ekranlarını 33 dilde, başlıklı bir
// çerçeve içinde çizer ve ekran görüntüsü alır. Yalnızca store-shots iş
// akışında çalışır (flutter drive). Çıktıyı tool/crop_store.py kırpar.
import 'dart:io';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:merkez_zihin_antrenmani/main.dart' as hub;
import 'package:studio_core/app/game_api.dart';
import 'package:studio_core/app/theme.dart';
import 'package:studio_core/app/widgets.dart';
import 'package:studio_core/core/game_rules.dart';
import 'package:studio_core/core/level_plan.dart';
import 'package:studio_core/core/strings.dart';

import 'store_texts.dart';

class _Shot {
  final String gameId;
  final int level;
  final Map<String, Object?> Function(GeneratedLevel g) resume;
  const _Shot(this.gameId, this.level, this.resume);
}

Map<String, Object?> _none(GeneratedLevel g) => const {};

const _shots = [
  _Shot('oyun-hafiza-dizisi', 20, _none),
  _Shot('oyun-stroop-testi', 20, _none),
  _Shot('oyun-schulte-tablosu', 20, _none),
  _Shot('oyun-oruntu-tamamlama', 20, _none),
  _Shot('oyun-uzamsal-dondurme', 20, _none),
  _Shot('oyun-gunluk-beyin-egzersizi-programi', 20, _none),
];

Widget _app(String lang, Widget child) => MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: buildTheme(hub.hubConfig.seedColor, Brightness.light),
      locale: Locale(lang),
      supportedLocales: Strings.languages.map(Locale.new).toList(),
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      home: child,
    );

/// Oyun ekranı: oyunun kendi çizimi, üstte başlık çubuğu (oyun içindeki gibi).
Widget _gameScreen(GameConfig cfg, GeneratedLevel g, Map<String, Object?> resume, String lang) {
  final strings = Strings(lang);
  final ctx = PlayContext(
    spec: g.spec,
    generated: g,
    resume: resume,
    pieceColors: Palettes.skin(0),
    background: Palettes.theme(g.spec.theme),
    colorBlind: false,
    reducedMotion: true,
    leftHanded: false,
    lang: lang,
    t: strings.t,
    finish: (_) {},
    saveResume: (_) {},
    requestHint: () async => false,
    requestBooster: () async => false,
    requestContinue: () async => false,
    sfx: (_) {},
  );
  return Scaffold(
    appBar: AppBar(
      title: Text('${cfg.localized(cfg.title, lang)} · ${strings.t('level', {'n': g.spec.levelId})}',
          overflow: TextOverflow.ellipsis),
      leading: const Icon(Icons.pause_circle),
    ),
    body: ThemedBackground(colors: Palettes.theme(g.spec.theme), child: SafeArea(child: cfg.buildPlay(ctx))),
  );
}

/// Görseller açılış konumunu gösterir; düşük zorluklu bölümler emülatörde hızlı doğrulanır.
/// Mağaza görseli: [box] mantıksal boyutunda, üstte başlık, ortada telefon
/// ya da tablet çerçevesinde oyun ekranı.
/// Başlığı iki satıra sığana kadar küçültür; hiçbir dilde kesilmez.
Widget _fitCaption(String text, double maxW, double maxH, double size) {
  var fs = size;
  TextStyle style() => TextStyle(
        color: Colors.white,
        fontWeight: FontWeight.w800,
        fontSize: fs,
        height: 1.15,
        shadows: const [Shadow(blurRadius: 8, color: Colors.black38)],
      );
  while (fs > 10) {
    final tp = TextPainter(text: TextSpan(text: text, style: style()), textDirection: TextDirection.ltr, maxLines: 2)
      ..layout(maxWidth: maxW);
    if (!tp.didExceedMaxLines && tp.height <= maxH) break;
    fs *= 0.92;
  }
  return Text(text, textAlign: TextAlign.center, maxLines: 2, style: style());
}

/// App Store görseli: cihaz çerçevesi YOK (Apple 2.3.3). Üstte isteğe bağlı
/// başlık bandı, altında oyun ekranı kenardan kenara, gerçek iOS mantıksal
/// boyutunda çizilir.
Widget _bleedFrame({required Size box, required String caption, required Widget screen, required bool rtl}) {
  final colors = Palettes.theme(3);
  final band = (box.height * 0.13).roundToDouble();
  final screenSize = Size(box.width, box.height - band);
  return Directionality(
    textDirection: rtl ? TextDirection.rtl : TextDirection.ltr,
    child: Align(
      alignment: Alignment.topLeft,
      child: SizedBox(
        width: box.width,
        height: box.height,
        child: Column(children: [
          Container(
            width: box.width,
            height: band,
            alignment: Alignment.center,
            padding: EdgeInsets.symmetric(horizontal: box.width * 0.06),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [hub.hubConfig.seedColor, colors.first],
              ),
            ),
            child: _fitCaption(caption, box.width * 0.88, band * 0.86, math.min(box.width, box.height) * 0.064),
          ),
          SizedBox(
            width: screenSize.width,
            height: screenSize.height,
            child: ClipRect(
              child: MediaQuery(
                data: MediaQueryData(size: screenSize, devicePixelRatio: 3, padding: EdgeInsets.zero),
                child: screen,
              ),
            ),
          ),
        ]),
      ),
    ),
  );
}

Widget _storeFrame({required Size box, required Size device, required String caption, required Widget screen, required bool rtl}) {
  final colors = Palettes.theme(3);
  return Directionality(
    textDirection: rtl ? TextDirection.rtl : TextDirection.ltr,
    child: Align(
      alignment: Alignment.topLeft,
      child: SizedBox(
        width: box.width,
        height: box.height,
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [hub.hubConfig.seedColor, colors.last, colors.first],
            ),
          ),
          child: Column(children: [
            SizedBox(
              height: box.height * 0.16,
              child: Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: box.width * 0.06),
                  child: _fitCaption(caption, box.width * 0.88, box.height * 0.15, math.min(box.width, box.height) * 0.072),
                ),
              ),
            ),
            Expanded(
              child: Padding(
                padding: EdgeInsets.fromLTRB(box.width * 0.07, 0, box.width * 0.07, box.height * 0.035),
                child: FittedBox(
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFF111318),
                      borderRadius: BorderRadius.circular(36),
                      boxShadow: const [BoxShadow(blurRadius: 30, color: Colors.black45, offset: Offset(0, 10))],
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(26),
                      child: SizedBox(
                        width: device.width,
                        height: device.height,
                        child: MediaQuery(
                          data: MediaQueryData(size: device, devicePixelRatio: 2.5, padding: EdgeInsets.zero),
                          child: screen,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ]),
        ),
      ),
    ),
  );
}

/// Öne çıkan görsel için sahne: renkli harf taşlarıyla tahmin satırları.
class _BoardPainter extends CustomPainter {
  const _BoardPainter();

  @override
  void paint(Canvas c, Size size) {
    final s = size.height * 0.16;
    final x0 = size.width / 2 - 2.5 * s, y0 = size.height / 2 - 1.6 * s;
    const rows = ['STONE', 'STORE', 'SCORE'];
    const cols = [Color(0xFF7B8494), Color(0xFFD9A441), Color(0xFF4F9A6E)];
    for (var r = 0; r < 3; r++) {
      for (var i = 0; i < 5; i++) {
        final rect = Rect.fromLTWH(x0 + i * s * 1.05, y0 + r * s * 1.1, s, s);
        final col = r == 2 ? cols[2] : cols[(i + r) % 3];
        c.drawRRect(RRect.fromRectAndRadius(rect.shift(Offset(0, s * 0.06)), Radius.circular(s * 0.18)), Paint()..color = Colors.black26);
        c.drawRRect(RRect.fromRectAndRadius(rect, Radius.circular(s * 0.18)), Paint()..color = col);
        final tp = TextPainter(
          text: TextSpan(text: rows[r][i], style: TextStyle(color: Colors.white, fontSize: s * 0.55, fontWeight: FontWeight.w800)),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(c, rect.center - Offset(tp.width / 2, tp.height / 2));
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/// Öne çıkan görsel (512×250 mantıksal = 1024×500 piksel, oran 2).
Widget _feature(String lang) {
  final rtl = Strings(lang).rtl;
  final colors = Palettes.theme(3);
  return Directionality(
    textDirection: rtl ? TextDirection.rtl : TextDirection.ltr,
    child: Align(
      alignment: Alignment.topLeft,
      child: SizedBox(
        width: 512,
        height: 250,
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [hub.hubConfig.seedColor, colors.first]),
          ),
          child: Row(children: [
            const SizedBox(width: 210, height: 250, child: CustomPaint(painter: _BoardPainter())),
            Expanded(
              child: Padding(
                padding: const EdgeInsetsDirectional.only(end: 22),
                child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: AlignmentDirectional.centerStart,
                    child: Text(Strings.pick(hub.hubConfig.title, lang),
                        maxLines: 1, style: const TextStyle(color: Colors.white, fontSize: 34, fontWeight: FontWeight.w900)),
                  ),
                  const SizedBox(height: 8),
                  Text(Strings.pick(hub.hubConfig.tagline, lang),
                      maxLines: 3,
                      style: const TextStyle(color: Color(0xEEFFFFFF), fontSize: 17, fontWeight: FontWeight.w600, height: 1.2)),
                ]),
              ),
            ),
          ]),
        ),
      ),
    ),
  );
}

/// Görüntü, ekran boyutundan bağımsız olarak [RepaintBoundary] ile çizilir;
/// böylece telefon ve tablet görselleri tek bir öykünücüde üretilir.
final _shotKey = GlobalKey();

Widget _offscreen(Size size, Widget child) => OverflowBox(
      alignment: Alignment.topLeft,
      minWidth: 0,
      minHeight: 0,
      maxWidth: double.infinity,
      maxHeight: double.infinity,
      child: RepaintBoundary(
          key: _shotKey,
          child: SizedBox(width: size.width, height: size.height, child: Material(type: MaterialType.transparency, child: child))),
    );

/// Görseli uygulamanın geçici klasörüne yazar; iş akışı adb ile çeker.
Future<void> _capture(WidgetTester tester, double pixelRatio, String name) async {
  final boundary = _shotKey.currentContext!.findRenderObject()! as RenderRepaintBoundary;
  await tester.runAsync(() async {
    final image = await boundary.toImage(pixelRatio: pixelRatio);
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    image.dispose();
    final f = File('${Directory.systemTemp.path}/shots/$name.png');
    f.createSync(recursive: true);
    f.writeAsBytesSync(data!.buffer.asUint8List());
  });
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('mağaza görselleri', (tester) async {
    await tester.pumpAndSettle();
    // Play: telefon 1080×1920 (9:16), tablet 1920×1080 (16:9), öne çıkan 1024×500
    // (başlıklı, genel cihaz çerçeveli). App Store: iPhone 6,9" 1290×2796 ve
    // iPad 13" 2732×2048, çerçevesiz tam ekran (iosphone_/iospad_).
    const kinds = <(String, Size, Size, double, bool)>[
      ('phone', Size(360, 640), Size(400, 800), 3, false),
      ('tablet', Size(1280, 720), Size(1000, 620), 1.5, false),
      ('iosphone', Size(430, 932), Size.zero, 3, true),
      ('iospad', Size(1366, 1024), Size.zero, 2, true),
    ];
    const only = String.fromEnvironment('LANGS');
    final langs = only.isEmpty ? Strings.languages : only.split(',');
    final games = {for (final g in hub.hubConfig.allGames) g.gameId: g};
    final built = <String, GeneratedLevel>{};
    var count = 0;
    for (final lang in langs) {
      final li = Strings.languages.indexOf(lang);
      for (final (kind, box, device, ratio, bleed) in kinds) {
        for (var k = 0; k < _shots.length; k++) {
          final shot = _shots[k];
          final cfg = games[shot.gameId]!;
          final g = built.putIfAbsent(shot.gameId,
              () => cfg.rules.build(LevelPlanner(gameId: cfg.gameId, optionalMechanics: cfg.rules.optionalMechanics).spec(shot.level)));
          await tester.pumpWidget(_app(
            lang,
            _offscreen(
              box,
              bleed
                  ? _bleedFrame(
                      box: box,
                      caption: storeCaptions[k][li],
                      rtl: Strings(lang).rtl,
                      screen: KeyedSubtree(key: ValueKey('${shot.gameId}-$lang-$kind'), child: _gameScreen(cfg, g, shot.resume(g), lang)),
                    )
                  : _storeFrame(
                      box: box,
                      device: device,
                      caption: storeCaptions[k][li],
                      rtl: Strings(lang).rtl,
                      screen: KeyedSubtree(key: ValueKey('${shot.gameId}-$lang-$kind'), child: _gameScreen(cfg, g, shot.resume(g), lang)),
                    ),
            ),
          ));
          for (var i = 0; i < 8; i++) {
            await tester.pump(const Duration(milliseconds: 150));
          }
          await _capture(tester, ratio, '${kind}_${lang}_${k + 1}');
          count++;
        }
      }
      await tester.pumpWidget(_app(lang, _offscreen(const Size(512, 250), _feature(lang))));
      await tester.pump(const Duration(milliseconds: 300));
      await _capture(tester, 2, 'feature_$lang');
      count++;
      // Bir sonraki dil için oyun ekranlarını temizle (zamanlayıcılar dursun).
      await tester.pumpWidget(const SizedBox());
    }
    binding.reportData = {'count': count};
  }, timeout: const Timeout(Duration(minutes: 55)));
}
