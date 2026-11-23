#!/usr/bin/env bash
# Mağaza görsellerini derleme makinesinde (Linux masaüstü, sanal ekran) çizer.
# Emülatör kullanılmaz: ağır bölüm denetimi ANR'ye yol açmaz, sistemdeki
# Noto yazı tipleri 33 dilin hepsini kapsar. Görseller /tmp/shots'a yazılır.
set -e
LANGS="${1:-tr,en,de,es,fr,ar,fa,he,ur,ru,uk,pl,cs,ro,hu,el,it,pt,nl,sv,da,nb,fi,ja,ko,zh,hi,bn,id,ms,th,vi,fil}"
IFS=',' read -ra ALL <<< "$LANGS"
rm -rf /tmp/shots
mkdir -p shots/raw
for ((i = 0; i < ${#ALL[@]}; i += 11)); do
  CHUNK=$(IFS=','; echo "${ALL[*]:i:11}")
  echo "== $CHUNK"
  xvfb-run -a -s "-screen 0 1920x1080x24" \
    flutter test integration_test/store_shots_test.dart -d linux --dart-define=LANGS="$CHUNK"
  cp /tmp/shots/*.png shots/raw/
  ls shots/raw | wc -l
done
