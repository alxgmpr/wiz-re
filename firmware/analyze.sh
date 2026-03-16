#!/usr/bin/env bash
# Analyze downloaded Wiz firmware images
# Extracts segment info useful for loading into Ghidra
set -euo pipefail

FIRMWARE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$FIRMWARE_DIR"

if ! command -v esptool.py &>/dev/null && ! command -v esptool &>/dev/null; then
  echo "esptool not found. Install with: pip install esptool"
  exit 1
fi

ESPTOOL=$(command -v esptool.py 2>/dev/null || command -v esptool)

for f in *.bin; do
  [ -f "$f" ] || continue
  echo "============================================"
  echo "  ${f} ($(wc -c < "$f") bytes)"
  echo "============================================"
  echo ""

  # Try ESP32-C6 first (our SHRGB bulb), then C3 (SHRGBW)
  if [[ "$f" == *SHRGB_* ]]; then
    CHIP="esp32c6"
  else
    CHIP="esp32c3"
  fi

  "$ESPTOOL" --chip "$CHIP" image_info -v 2 "$f" 2>&1 || \
    echo "  Failed to parse with chip ${CHIP}"
  echo ""

  # Extract segment offsets for Ghidra loading
  # esptool prints lines like: "Segment N: len 0xNNNNN load 0xNNNNNNNN file_offs 0xNNNNNNNN"
  echo "--- Ghidra loading commands ---"
  echo "Chip: ${CHIP} (RISC-V RV32IMC)"
  echo "Use 'Add to Program' in Ghidra to load additional segments."
  echo "Set language to: RISCV:LE:32:RV32IMC"
  echo ""

  # Generate dd commands to extract segments (data starts 8 bytes after file_offs)
  "$ESPTOOL" --chip "$CHIP" image_info -v 2 "$f" 2>/dev/null | \
    python3 -c "
import sys
for line in sys.stdin:
    line = line.strip()
    if 'Segment' in line and 'len' in line and 'load' in line and 'file_offs' in line:
        parts = line.split()
        seg = parts[1].rstrip(':')
        for i, p in enumerate(parts):
            if p == 'len': length = int(parts[i+1], 16)
            if p == 'load': load_addr = parts[i+1]
            if p == 'file_offs': file_off = int(parts[i+1], 16)
        # Data starts 8 bytes after the segment header offset
        data_off = file_off + 8
        print(f'dd if={\"$f\"} bs=1 count={length} skip={data_off} of=seg{seg}_{load_addr}.bin')
" 2>/dev/null || echo "  (could not extract segments)"

  echo ""
done
