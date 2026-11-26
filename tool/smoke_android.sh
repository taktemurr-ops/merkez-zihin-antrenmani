#!/usr/bin/env bash
# Device smoke test on a running Android emulator (see device-smoke.yml).
# Exit 1: the app crashed / ANR / stopped running. Exit 2: the emulator was
# lost (adb offline / not found) - an infrastructure failure; the workflow
# retries once on a fresh emulator.
set -u
NAME="${1:-device}"
mkdir -p smoke
PKG=$(grep -hm1 'applicationId' android/app/build.gradle* | sed -E 's/.*"([^"]+)".*/\1/')
echo "package: $PKG"
T() { timeout -k 10 "$@"; }
device_ok() { [ "$(T 15 adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; }
infra() {
  echo "::warning::emulator lost during: $1"
  T 30 adb devices -l || true
  exit 2
}
# A hung or failed adb step fails fast with diagnostics instead of hitting
# the job timeout.
hang() {
  device_ok || infra "$1"
  echo "::error::smoke step failed: $1"
  T 30 adb shell pidof "$PKG" || echo "app process not running"
  T 30 adb shell dumpsys activity top | head -40 || true
  T 60 adb logcat -d > "smoke/$NAME-logcat.txt" || true
  grep -E "FATAL|ANR|$PKG" "smoke/$NAME-logcat.txt" | tail -80 || true
  exit 1
}
# Wait until the device is fully up (package manager answers) and settled.
ready=0
for _ in $(seq 1 60); do
  if device_ok && T 15 adb shell pm path android > /dev/null 2>&1; then ready=1; break; fi
  sleep 3
done
[ "$ready" = 1 ] || infra "boot"
sleep 10
T 180 adb install -r build/app/outputs/flutter-apk/app-release.apk || hang "install"
T 30 adb logcat -c || true
T 60 adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 || hang "launch"
sleep 25
T 90 adb exec-out screencap -p > "smoke/$NAME-start.png" || hang "screencap (start)"
# ~500 random taps/swipes inside the app (fixed seed = reproducible).
T 300 adb shell monkey -p "$PKG" --pct-touch 75 --pct-motion 20 --pct-nav 0 --pct-majornav 5 --pct-syskeys 0 \
  --throttle 120 -s 42 500 > "smoke/$NAME-monkey.txt" 2>&1 || hang "monkey"
sleep 3
T 90 adb exec-out screencap -p > "smoke/$NAME-after.png" || hang "screencap (after)"
T 60 adb logcat -d > "smoke/$NAME-logcat.txt" || hang "logcat"
if grep -E "FATAL EXCEPTION|ANR in $PKG|// CRASH" "smoke/$NAME-logcat.txt" "smoke/$NAME-monkey.txt"; then
  echo "Crash or ANR detected"
  grep -A40 "FATAL EXCEPTION" "smoke/$NAME-logcat.txt" | head -120 || true
  grep -A40 "// CRASH" "smoke/$NAME-monkey.txt" | head -60 || true
  exit 1
fi
if ! T 30 adb shell pidof "$PKG" > /dev/null; then
  device_ok || infra "final check"
  echo "App process is not running"; exit 1
fi
echo "Android smoke test passed on $NAME"
