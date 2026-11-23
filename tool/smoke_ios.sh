#!/usr/bin/env bash
# Device smoke test on iPhone and iPad simulators (see device-smoke.yml).
set -u
APP=build/ios/iphonesimulator/Runner.app
BID=$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$APP/Info.plist")
echo "bundle id: $BID"
mkdir -p smoke
status=0
for DEV in iPhone iPad; do
  UDID=$(xcrun simctl list devices available | grep -E "^[[:space:]]+$DEV" | head -1 | grep -oE '[0-9A-F-]{36}')
  if [ -z "$UDID" ]; then echo "no $DEV simulator"; status=1; continue; fi
  xcrun simctl boot "$UDID" 2>/dev/null || true
  xcrun simctl bootstatus "$UDID" -b
  xcrun simctl install "$UDID" "$APP"
  xcrun simctl launch "$UDID" "$BID"
  sleep 40
  xcrun simctl io "$UDID" screenshot "smoke/ios-$DEV.png" || true
  if xcrun simctl spawn "$UDID" launchctl list | grep -q "$BID"; then
    echo "$DEV: app running"
  else
    echo "$DEV: app is not running (crash?)"; status=1
  fi
  xcrun simctl shutdown "$UDID" || true
done
exit $status
