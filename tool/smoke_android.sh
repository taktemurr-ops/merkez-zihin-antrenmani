#!/usr/bin/env bash
# Device smoke test on a running Android emulator (device-smoke.yml and
# device-matrix.yml). Usage: smoke_android.sh NAME
#   SMOKE_WM=720x1280@320  optional screen override (wm size/density) to
#                          emulate a smaller phone on any profile.
#   SMOKE_APK / SMOKE_ITEST_APK  release APK / on-device test APK (app hubs).
# Steps: install, launch, rotate, background/foreground, per-app RTL language
# (API 33+), ~500 random taps (monkey), and for app hubs an on-device test that
# opens tools from every category in tr/ar/en and reports layout problems.
# Screenshots of every step go to smoke/.
# Exit 1: our app crashed / ANR / layout errors / stopped running.
# Exit 2: the emulator was lost (adb offline / not found) - an infrastructure
# failure; the workflow retries once on a fresh emulator.
set -u
NAME="${1:-device}"
mkdir -p smoke
APK="${SMOKE_APK:-build/app/outputs/flutter-apk/app-release.apk}"
ITEST_APK="${SMOKE_ITEST_APK:-build/app/outputs/flutter-apk/app-debug.apk}"
if [ -n "${SMOKE_PKG:-}" ]; then PKG="$SMOKE_PKG"
elif [ -f smoke-pkg.txt ]; then PKG=$(cat smoke-pkg.txt)
else PKG=$(grep -hm1 'applicationId' android/app/build.gradle* | sed -E 's/.*"([^"]+)".*/\1/'); fi
echo "package: $PKG"
T() { timeout -k 10 "$@"; }
device_ok() { [ "$(T 15 adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; }
infra() {
  echo "::warning::emulator lost during: $1"
  T 30 adb devices -l || true
  echo "--- son monkey olayları ---"; tail -25 "smoke/$NAME-monkey.txt" 2>/dev/null || true
  echo "--- canlı logcat (son 120 satır) ---"; tail -120 "smoke/$NAME-live-logcat.txt" 2>/dev/null || true
  echo "--- nabız ---"; tail -15 "smoke/$NAME-heartbeat.txt" 2>/dev/null || true
  echo "--- ana makine belleği / OOM ---"; free -m || true
  sudo -n dmesg 2>/dev/null | grep -iE "out of memory|killed process|oom-kill" | tail -5 || true
  echo "infra" > "smoke/$NAME-result.txt"
  exit 2
}
fail() {
  echo "::error::$NAME: $1"
  echo "app: $1" > "smoke/$NAME-result.txt"
  exit 1
}
# A hung or failed adb step fails fast with diagnostics instead of hitting
# the job timeout.
hang() {
  device_ok || infra "$1"
  echo "::error::smoke step failed: $1"
  tail -25 "smoke/$NAME-monkey.txt" 2>/dev/null || true
  T 30 adb shell pidof "$PKG" || echo "app process not running"
  T 30 adb shell dumpsys activity top | head -40 || true
  T 60 adb logcat -d > "smoke/$NAME-logcat.txt" || true
  grep -E "FATAL|ANR|$PKG" "smoke/$NAME-logcat.txt" | tail -80 || true
  fail "step failed: $1"
}
SHOT=0
shot() {
  SHOT=$((SHOT + 1))
  T 90 adb exec-out screencap -p > "smoke/$NAME-$(printf %02d $SHOT)-$1.png" || hang "screencap ($1)"
}
pause() { sleep "$1"; }
launch() { T 60 adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 > /dev/null || hang "launch"; }
alive() { T 30 adb shell pidof "$PKG" | tr -d '\r'; }
# Our process only: crash (FATAL EXCEPTION) or ANR in logcat / monkey output.
crashed() {
  T 60 adb logcat -d > "smoke/$NAME-logcat.txt" || hang "logcat"
  if grep -A1 "FATAL EXCEPTION" "smoke/$NAME-logcat.txt" | grep -q "Process: $PKG," \
    || grep -qE "ANR in $PKG|// CRASH: $PKG|// NOT RESPONDING: $PKG" "smoke/$NAME-logcat.txt" "smoke/$NAME-monkey.txt" 2>/dev/null; then
    echo "Crash or ANR detected ($1)"
    grep -A40 "Process: $PKG," "smoke/$NAME-logcat.txt" | head -120 || true
    grep -B2 -A20 "ANR in $PKG" "smoke/$NAME-logcat.txt" | head -60 || true
    grep -A40 "// CRASH: $PKG" "smoke/$NAME-monkey.txt" 2>/dev/null | head -60 || true
    return 0
  fi
  return 1
}

# Wait until the device is fully up (package manager answers) and settled.
ready=0
for _ in $(seq 1 60); do
  if device_ok && T 15 adb shell pm path android > /dev/null 2>&1; then ready=1; break; fi
  sleep 3
done
[ "$ready" = 1 ] || infra "boot"
sleep 10
SDK=$(T 15 adb shell getprop ro.build.version.sdk | tr -d '\r')
echo "API level: $SDK"
if [ -n "${SMOKE_WM:-}" ]; then
  T 20 adb shell wm size "${SMOKE_WM%@*}" || true
  T 20 adb shell wm density "${SMOKE_WM#*@}" || true
  sleep 3
fi
T 20 adb shell wm size | tr '\n' ' '; T 20 adb shell wm density | tr '\n' ' '; echo
# Arka planda eşitleme yapan, testle ilgisiz önyüklü uygulamalar kapatılır
# (ör. e-posta istemcisinin kendi çökmesi testi düşürmesin).
for p in com.google.android.gm com.google.android.youtube com.google.android.apps.maps com.android.chrome; do
  T 20 adb shell pm disable-user --user 0 "$p" > /dev/null 2>&1 || true
done
T 240 adb install -r -g "$APK" || hang "install"
T 30 adb logcat -c || true
# Emülatör düşerse son durumu görebilmek için canlı logcat ve nabız kaydı.
adb logcat -v time '*:I' > "smoke/$NAME-live-logcat.txt" 2>&1 &
LOGCAT_PID=$!
( while true; do
    echo "$(date +%T) $(T 8 adb shell 'cat /proc/loadavg; grep -E "MemAvailable" /proc/meminfo' 2>&1 | tr '\n' ' ')"
    sleep 10
  done ) > "smoke/$NAME-heartbeat.txt" 2>&1 &
BEAT_PID=$!
trap 'kill $LOGCAT_PID $BEAT_PID 2>/dev/null || true' EXIT

# 1) Açılış.
launch
pause 25
shot start
[ -n "$(alive)" ] || { crashed launch; fail "app not running after launch"; }

# 2) Döndürme: yatay, sonra yeniden dikey (oyunlarda telefonlar dikey kilitli).
T 20 adb shell settings put system accelerometer_rotation 0 || true
T 20 adb shell settings put system user_rotation 1 || true
pause 6
shot landscape
T 20 adb shell settings put system user_rotation 0 || true
pause 5
shot portrait
[ -n "$(alive)" ] || { crashed rotate; fail "app stopped after rotation"; }

# 3) Arka plan / ön plan: ana ekran, sonra geri dön (süreç korunmalı).
PID1=$(alive)
T 20 adb shell input keyevent KEYCODE_HOME || hang "home key"
pause 8
launch
pause 6
shot resumed
PID2=$(alive)
[ -n "$PID2" ] || { crashed resume; fail "app not running after background/foreground"; }
[ "$PID1" = "$PID2" ] || echo "::notice::$NAME: süreç arka planda yeniden başlatıldı ($PID1 -> $PID2)"

# 4) Sağdan sola dil (uygulamaya özel dil, Android 13+): Arapça.
RTL=0
if [ "${SDK:-0}" -ge 33 ]; then
  if T 30 adb shell cmd locale set-app-locales "$PKG" --user 0 --locales ar-SA; then
    RTL=1
    pause 8
    launch
    pause 8
    shot rtl-ar
    [ -n "$(alive)" ] || { crashed rtl; fail "app stopped after switching to Arabic"; }
  fi
else
  echo "API $SDK < 33: uygulama dili komutu yok, RTL widget testlerinde denenir"
fi

# 5) ~500 rastgele dokunuş/kaydırma (sabit tohum = tekrarlanabilir).
# Monkey başka süreçlerin çökmesinde durmasın; yalnızca bu uygulamanın
# çökmesi/ANR'si aşağıda ayrıca denetlenir.
T 300 adb shell monkey -p "$PKG" --ignore-crashes --ignore-timeouts --ignore-security-exceptions --pct-touch 75 --pct-motion 20 --pct-nav 0 --pct-majornav 5 --pct-syskeys 0 \
  --throttle 120 -s 42 500 > "smoke/$NAME-monkey.txt" 2>&1 || hang "monkey"
sleep 3
shot after-monkey
[ "$RTL" = 1 ] && T 30 adb shell cmd locale set-app-locales "$PKG" --user 0 --locales tr-TR > /dev/null 2>&1
if crashed monkey; then fail "crash or ANR"; fi
other=$(grep -A1 "FATAL EXCEPTION" "smoke/$NAME-logcat.txt" | grep -o "Process: [^,]*" | sort -u | tr '\n' ' ')
[ -n "$other" ] && echo "::notice::başka süreçlerde çökme (uygulama dışı, yok sayıldı): $other"
if [ -z "$(alive)" ]; then
  device_ok || infra "final check"
  fail "app process is not running"
fi

# 6) Uygulama merkezleri: cihazda araç gezintisi testi (tr / ar / en; her
# kategoriden araçlar; taşma, kesik metin, erişilemeyen düğme denetimi).
if [ -f "$ITEST_APK" ] && [ "${SMOKE_ITEST:-1}" = 1 ]; then
  echo "== cihazda araç gezintisi ($ITEST_APK)"
  T 60 adb uninstall "$PKG" > /dev/null 2>&1 || true
  T 480 adb install -r -g "$ITEST_APK" || hang "install test apk"
  T 30 adb logcat -c || true
  launch
  done_=0
  for i in $(seq 1 90); do
    sleep 10
    [ $((i % 3)) = 1 ] && shot "gezinti-$i"
    T 60 adb logcat -d -s flutter:I > "smoke/$NAME-itest.txt" 2>/dev/null || true
    if grep -qE "DEVICE_SMOKE_(OK|FAIL)" "smoke/$NAME-itest.txt"; then done_=1; break; fi
    if [ -z "$(alive)" ]; then break; fi
    device_ok || infra "on-device test"
  done
  shot gezinti-son
  grep -E "SORUN\||BOYUT|DEVICE_SMOKE|EXCEPTION|overflowed" "smoke/$NAME-itest.txt" | sed 's/^.*flutter[^:]*: //' | head -150
  if crashed itest; then fail "crash during on-device tool test"; fi
  if [ "$done_" != 1 ]; then
    tail -40 "smoke/$NAME-itest.txt"
    [ -n "$(alive)" ] || fail "test app stopped during on-device tool test"
    fail "on-device tool test did not finish in 15 minutes"
  fi
  grep -q "DEVICE_SMOKE_OK" "smoke/$NAME-itest.txt" || fail "layout problems found on device (see SORUN lines)"
fi
echo "ok" > "smoke/$NAME-result.txt"
echo "Android smoke test passed on $NAME"
