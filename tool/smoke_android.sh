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
  echo "--- son monkey olayları ---"; tail -25 "smoke/$NAME-monkey.txt" 2>/dev/null || true
  echo "--- canlı logcat (son 120 satır) ---"; tail -120 "smoke/$NAME-live-logcat.txt" 2>/dev/null || true
  echo "--- nabız ---"; tail -15 "smoke/$NAME-heartbeat.txt" 2>/dev/null || true
  echo "--- ana makine belleği / OOM ---"; free -m || true
  sudo -n dmesg 2>/dev/null | grep -iE "out of memory|killed process|oom-kill" | tail -5 || true
  exit 2
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
# Arka planda eşitleme yapan, testle ilgisiz önyüklü uygulamalar kapatılır
# (ör. e-posta istemcisinin kendi çökmesi testi düşürmesin).
for p in com.google.android.gm com.google.android.youtube com.google.android.apps.maps com.android.chrome; do
  T 20 adb shell pm disable-user --user 0 "$p" > /dev/null 2>&1 || true
done
T 180 adb install -r build/app/outputs/flutter-apk/app-release.apk || hang "install"
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
T 60 adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 || hang "launch"
sleep 25
T 90 adb exec-out screencap -p > "smoke/$NAME-start.png" || hang "screencap (start)"
# ~500 random taps/swipes inside the app (fixed seed = reproducible).
# Monkey başka süreçlerin çökmesinde durmasın; yalnızca bu uygulamanın
# çökmesi/ANR'si aşağıda ayrıca denetlenir.
T 300 adb shell monkey -p "$PKG" --ignore-crashes --ignore-timeouts --ignore-security-exceptions --pct-touch 75 --pct-motion 20 --pct-nav 0 --pct-majornav 5 --pct-syskeys 0 \
  --throttle 120 -s 42 500 > "smoke/$NAME-monkey.txt" 2>&1 || hang "monkey"
sleep 3
T 90 adb exec-out screencap -p > "smoke/$NAME-after.png" || hang "screencap (after)"
T 60 adb logcat -d > "smoke/$NAME-logcat.txt" || hang "logcat"
# Yalnızca bu uygulamaya ait çökme/ANR sayılır (başka süreçlerinki değil).
if grep -A1 "FATAL EXCEPTION" "smoke/$NAME-logcat.txt" | grep -q "Process: $PKG," \
  || grep -qE "ANR in $PKG|// CRASH: $PKG|// NOT RESPONDING: $PKG" "smoke/$NAME-logcat.txt" "smoke/$NAME-monkey.txt"; then
  echo "Crash or ANR detected"
  grep -A40 "Process: $PKG," "smoke/$NAME-logcat.txt" | head -120 || true
  grep -A40 "// CRASH: $PKG" "smoke/$NAME-monkey.txt" | head -60 || true
  exit 1
fi
other=$(grep -A1 "FATAL EXCEPTION" "smoke/$NAME-logcat.txt" | grep -o "Process: [^,]*" | sort -u | tr '\n' ' ')
[ -n "$other" ] && echo "::notice::başka süreçlerde çökme (uygulama dışı, yok sayıldı): $other"
if ! T 30 adb shell pidof "$PKG" > /dev/null; then
  device_ok || infra "final check"
  echo "App process is not running"; exit 1
fi
echo "Android smoke test passed on $NAME"
