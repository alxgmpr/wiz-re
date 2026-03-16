#!/usr/bin/env bash
# Download Wiz bulb firmware from firmware.wiz.world
set -euo pipefail

FIRMWARE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$FIRMWARE_DIR"

MODULE="ESP24_SHRGB_01"
BASE_URL="http://firmware.wiz.world/firmwares"

# Versions to try (newest first)
VERSIONS=("1.36.1" "1.30.1" "1.28.0" "1.22.59")

# Also try the SHRGBW variant (ESP32-C3 based, from issue thread)
MODULES=("ESP24_SHRGB_01" "ESP24_SHRGBW_01")

for mod in "${MODULES[@]}"; do
  for ver in "${VERSIONS[@]}"; do
    URL="${BASE_URL}/${mod}/${ver}/wizlight.bin"
    OUTFILE="${mod}_${ver}.bin"

    if [ -f "$OUTFILE" ]; then
      echo "[skip] ${OUTFILE} already exists ($(wc -c < "$OUTFILE") bytes)"
      continue
    fi

    echo -n "[fetch] ${URL} ... "
    HTTP_CODE=$(curl -s -o "$OUTFILE" -w "%{http_code}" "$URL" 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" = "200" ] && [ -s "$OUTFILE" ]; then
      SIZE=$(wc -c < "$OUTFILE")
      echo "OK (${SIZE} bytes)"
    else
      rm -f "$OUTFILE"
      echo "FAILED (HTTP ${HTTP_CODE})"
    fi
  done
done

echo ""
echo "Downloaded firmware files:"
ls -lh *.bin 2>/dev/null || echo "  (none)"

# Run esptool analysis if available
if command -v esptool.py &>/dev/null; then
  echo ""
  echo "=== esptool.py analysis ==="
  for f in *.bin; do
    [ -f "$f" ] || continue
    echo ""
    echo "--- ${f} ---"
    # Try C6 first (our bulb), fall back to C3
    esptool.py --chip esp32c6 image_info -v 2 "$f" 2>/dev/null || \
    esptool.py --chip esp32c3 image_info -v 2 "$f" 2>/dev/null || \
    echo "  (could not parse)"
  done
elif command -v esptool &>/dev/null; then
  echo ""
  echo "=== esptool analysis ==="
  for f in *.bin; do
    [ -f "$f" ] || continue
    echo ""
    echo "--- ${f} ---"
    esptool --chip esp32c6 image_info -v 2 "$f" 2>/dev/null || \
    esptool --chip esp32c3 image_info -v 2 "$f" 2>/dev/null || \
    echo "  (could not parse)"
  done
else
  echo ""
  echo "Install esptool for firmware analysis: pip install esptool"
fi
