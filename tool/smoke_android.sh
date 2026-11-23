#!/usr/bin/env bash
# Device smoke test on a running Android emulator (see device-smoke.yml).
set -u
NAME="${1:-device}"
mkdir -p smoke
PKG=$(grep -hm1 'applicationId' android/app/build.gradle* | sed -E 's/.*"([^"]+)".*/\1/')
echo "package: $PKG"
adb install -r build/app/outputs/flutter-apk/app-release.apk || exit 1
adb logcat -c
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1
sleep 25
adb exec-out screencap -p > "smoke/$NAME-start.png"
# ~500 random taps/swipes inside the app (fixed seed = reproducible).
adb shell monkey -p "$PKG" --pct-touch 75 --pct-motion 20 --pct-nav 0 --pct-majornav 5 \
  --throttle 120 -s 42 500 > "smoke/$NAME-monkey.txt" 2>&1
sleep 3
adb exec-out screencap -p > "smoke/$NAME-after.png"
adb logcat -d > "smoke/$NAME-logcat.txt"
if grep -E "FATAL EXCEPTION|ANR in $PKG|// CRASH" "smoke/$NAME-logcat.txt" "smoke/$NAME-monkey.txt"; then
  echo "Crash or ANR detected"
  grep -A40 "FATAL EXCEPTION" "smoke/$NAME-logcat.txt" | head -120 || true
  grep -A40 "// CRASH" "smoke/$NAME-monkey.txt" | head -60 || true
  exit 1
fi
if ! adb shell pidof "$PKG" > /dev/null; then
  echo "App process is not running"; exit 1
fi
echo "Android smoke test passed on $NAME"
