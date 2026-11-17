# Wiz Bulb RE

Reverse engineering the [Wiz Connected](https://www.wizconnected.com/) smart bulb platform. The target is a PureSmart TruColor RGBWW bulb (ESP24_SHRGB_01), but most of the protocol findings apply to the entire Wiz product line.

## Why

The Wiz app and cloud service work fine for basic control, but large parts of the protocol are undocumented or locked behind MQTT-only access. We wanted to understand the full protocol surface — every method the firmware exposes, what parameters they accept, and which ones are arbitrarily gated to cloud-only. Along the way we built tools to intercept MQTT, patch the firmware to unlock restricted methods over UDP, and convert firmware images to ELF for static analysis.

The existing community knowledge (mainly from [pywizlight](https://github.com/sbidy/pywizlight) and [its issues](https://github.com/sbidy/pywizlight/issues/155)) covers about 15 methods. The firmware actually implements 74+ methods, many of which are undocumented. This repo documents what we found.

## What's here

### Protocol documentation

[**PROTOCOL.md**](PROTOCOL.md) is the main reference. Covers all 74 methods in firmware 1.36.1, organized by access type (UDP vs MQTT-only), with parameter formats, error codes, and cross-version diffs from 1.21.14 through 1.36.99.

Key findings:
- The firmware dispatch table has per-method flags controlling UDP vs MQTT access. 35 methods are UDP-accessible, 37 are MQTT-only.
- `setEffect` uses nested object keys as mode selectors (`{"preview": {...}}`), not a flat `mode` param. Supports preview, pulse, stepOff, autobrightness, and ambienceSync modes.
- `setPilot` silently ignores `fadeIn`/`fadeOut` parameters — fade is a global setting only configurable via `setUserConfig` (MQTT-only). Confirmed by decompiling the handler.
- The CCT table mapping color temperatures to 5-channel RGBWC values is readable via `getCctTable` and writable via `setCctTable` (MQTT-only).
- `w` and `c` params on `setPilot` directly set warm/cold white channels, bypassing the CCT table.

### UDP control tool

`tools/wiz_udp.py` — Zero-dependency Python CLI for direct bulb control over UDP port 38899.

```bash
python3 tools/wiz_udp.py get-pilot
python3 tools/wiz_udp.py set-pilot --on --dimming 50 --temp 3000
python3 tools/wiz_udp.py set-effect --mode preview --duration 10 --cct 4000
python3 tools/wiz_udp.py fade --from-dimming 10 --to-dimming 100 --duration 3 --steps 30
python3 tools/wiz_udp.py raw '{"method":"getModelConfig","params":{}}'
```

Supports setPilot, setState, setEffect (all modes), pulse, fade ramping, and every get* query. Set `WIZ_IP` (required) and `WIZ_PORT` env vars, or pass `--ip`/`--port`.

### MQTT interception

`mqtt/` — Local Mosquitto broker setup to man-in-the-middle the bulb's cloud MQTT connection (eu.mqtt.wiz.world:8883). This unlocks methods like `setUserConfig`, `setFavs`, `updateOta`, and `reboot` that the firmware refuses to execute over UDP.

```bash
cd mqtt && bash setup.sh          # generates certs, starts broker
export WIZ_MAC=<mac> WIZ_HOME_ID=<homeId>   # both from: tools/wiz_udp.py get-system-config
./mqtt/send_mqtt.sh '{"method":"setUserConfig","params":{"fadeIn":700,"fadeOut":700,"userConfigTs":2}}'
```

Requires DNS redirect (dnsmasq, /etc/hosts, or router) so the bulb connects to your broker instead of Wiz's cloud. See `mqtt/examples.sh` for common commands.

### Firmware analysis

`firmware/` — Tools for static analysis of stock firmware images.

- **esp2elf.py** — Converts ESP-IDF OTA images to ELF32 RISC-V binaries for Ghidra or Binary Ninja. Parses the image header, extracts DROM/DRAM/IRAM/IROM segments with correct load addresses and permissions.
- **patch_firmware.py** — Binary patches the method dispatch table to unlock MQTT-only methods over UDP. Changes the access flags from 0x04 (cloud-only) to 0x0606 (local+cloud), then recalculates the ESP-IDF checksum and SHA256 hash.
- **serve_ota.py** — HTTP server on port 80 that serves firmware to the bulb during OTA. Supports bait-and-switch mode (serve original on retries, patched on first download).
- **download_firmware.sh** — Downloads firmware images from firmware.wiz.world. We analyzed versions 1.21.14 through 1.36.99; `versions_shrgb.txt` lists every SHRGB version found on the server.
- **analyze.sh** — Runs `esptool image_info` on downloaded images and prints `dd` commands to extract segments.
- **dump_dispatch_table.py** — Extracts the full dispatch table from a firmware binary, showing every method name, handler address, and access flags.
- **espimage.py** — Shared image/segment/dispatch-table parsing used by the tools above. `python3 firmware/test_espimage.py` self-checks it on a synthetic image.

```bash
# Convert to ELF for disassembly
python3 firmware/esp2elf.py firmware/ESP24_SHRGB_01_1.36.1.bin

# Patch and serve
python3 firmware/patch_firmware.py firmware/ESP24_SHRGB_01_1.36.1.bin
sudo python3 firmware/serve_ota.py firmware/ESP24_SHRGB_01_1.36.1.patched.bin
```

### Method discovery tools

These send real commands to a live bulb (`WIZ_IP` or `--ip`). Calls that can reset, reboot, or reconfigure the bulb are skipped unless you pass `--dangerous`.

- **tools/probe_all_methods.py** — Sends ~120 calls covering 69 methods, categorizing responses as OK, error (with code), or timeout. Writes `probe_results.json` (gitignored; contains your device IDs).
- **tools/probe_effects_and_params.py** — Parameter probing for setEffect, pulse, registration, setPilot extras, and getSensor. Leaves the bulb at 2700K/100%.

### ESPHome config

`wiz.yaml` — ESPHome replacement firmware config for the bulb. Targets an ESP32-C6 module we swapped in for the stock ESP32-C3, driving the bulb's BP5758D LED driver (5 RGBWW channels). This is a nuclear option — complete firmware replacement that gives you full local control but loses all stock Wiz functionality.

## Hardware

- **Bulb:** Wiz PureSmart TruColor (ESP24_SHRGB_01)
- **Chip:** ESP32-C3 (RISC-V RV32IMC) — the "ESP24" marketing name is misleading. Our ESPHome build runs on a replacement ESP32-C6 module.
- **LED driver:** BP5758D over I2C, 5 channels: Blue(ch3), Green(ch2), Red(ch1), Warm White(ch4), Cold White(ch5)
- **Color temp range:** 1500K–6500K
- **UDP port:** 38899
- **MQTT broker:** eu.mqtt.wiz.world:8883 (TLS)

## Related work

- [pywizlight](https://github.com/sbidy/pywizlight) — Python library for Wiz bulbs, covers ~15 methods. Powers the Home Assistant integration. [Issue #155](https://github.com/sbidy/pywizlight/issues/155) has community protocol notes that were a starting point for this work.
- [Wiz Pro API docs](https://docs.pro.wizconnected.com/) — Official docs for the commercial/pro line. Some overlap with consumer protocol but not 1:1.
