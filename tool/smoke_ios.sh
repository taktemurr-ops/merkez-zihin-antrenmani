#!/usr/bin/env bash
# Device smoke test on iOS simulators (device-smoke.yml / device-matrix.yml).
# Usage: smoke_ios.sh ["iPhone|iPad"]   (|-separated name patterns; the first
# available simulator matching each pattern is used, in order of preference
# inside a pattern written as "iPhone SE~iPhone 1" = try SE, else any).
# Steps per simulator: install, launch, background/foreground (Settings app),
# relaunch in Arabic (right-to-left) and English, check the app is still
# running and no crash report was written; screenshots to smoke/.
set -u
PATTERNS="${1:-iPhone|iPad}"
APP=build/ios/iphonesimulator/Runner.app
BID=$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$APP/Info.plist")
EXE=$(/usr/libexec/PlistBuddy -c 'Print CFBundleExecutable' "$APP/Info.plist")
echo "bundle id: $BID"
mkdir -p smoke
xcrun simctl list runtimes available | grep -i ios || true
status=0
DIAG="$HOME/Library/Logs/DiagnosticReports"
running() { xcrun simctl spawn "$1" launchctl list | grep -q "$BID"; }
crash_reports() { ls -t "$DIAG" 2>/dev/null | grep -E "^($EXE|Runner)[-_.]" || true; }
IFS='|' read -ra PATS <<< "$PATTERNS"
for PAT in "${PATS[@]}"; do
  UDID=""
  IFS='~' read -ra ALTS <<< "$PAT"
  for ALT in "${ALTS[@]}"; do
    LINE=$(xcrun simctl list devices available | grep -E "^[[:space:]]+$ALT" | head -1)
    UDID=$(echo "$LINE" | grep -oE '[0-9A-F-]{36}' | head -1)
    [ -n "$UDID" ] && break
  done
  if [ -z "$UDID" ]; then echo "::warning::no simulator for '$PAT'"; continue; fi
  DEV=$(echo "$LINE" | sed -E 's/^[[:space:]]+//; s/ \([0-9A-F-]{36}\).*//')
  TAG=$(echo "$DEV" | tr -c 'A-Za-z0-9\n' '_' | tr -s '_')
  echo "== $DEV ($UDID)"
  before=$(crash_reports | wc -l)
  xcrun simctl boot "$UDID" 2>/dev/null || true
  xcrun simctl bootstatus "$UDID" -b > /dev/null
  xcrun simctl install "$UDID" "$APP"
  xcrun simctl launch "$UDID" "$BID" -AppleLanguages "(tr)" -AppleLocale tr_TR > /dev/null
  sleep 40
  xcrun simctl io "$UDID" screenshot "smoke/ios-$TAG-1-start.png" > /dev/null 2>&1 || true
  ok=1
  running "$UDID" || { echo "$DEV: app is not running after launch (crash?)"; ok=0; }
  # Arka plan / ön plan.
  xcrun simctl launch "$UDID" com.apple.Preferences > /dev/null 2>&1 || true
  sleep 6
  xcrun simctl launch "$UDID" "$BID" > /dev/null
  sleep 8
  xcrun simctl io "$UDID" screenshot "smoke/ios-$TAG-2-resumed.png" > /dev/null 2>&1 || true
  running "$UDID" || { echo "$DEV: app is not running after background/foreground"; ok=0; }
  # Sağdan sola: Arapça ile yeniden aç; sonra İngilizce.
  for L in ar en; do
    xcrun simctl terminate "$UDID" "$BID" > /dev/null 2>&1 || true
    xcrun simctl launch "$UDID" "$BID" -AppleLanguages "($L)" -AppleLocale "$L" > /dev/null
    sleep 20
    xcrun simctl io "$UDID" screenshot "smoke/ios-$TAG-3-$L.png" > /dev/null 2>&1 || true
    running "$UDID" || { echo "$DEV: app is not running in '$L'"; ok=0; }
  done
  after=$(crash_reports | wc -l)
  if [ "$after" -gt "$before" ]; then
    echo "$DEV: crash report written:"; crash_reports | head -3
    head -60 "$DIAG/$(crash_reports | head -1)" || true
    ok=0
  fi
  if [ "$ok" = 1 ]; then echo "$DEV: OK" | tee -a smoke/ios-results.txt; else echo "$DEV: FAIL" | tee -a smoke/ios-results.txt; status=1; fi
  xcrun simctl shutdown "$UDID" || true
done
exit $status
