# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hacking toolkit for a **PureSmart TruColor** Wiz smart light bulb. Includes ESPHome replacement firmware config, a UDP control CLI, MQTT interception setup, and stock firmware for reverse engineering.

**Bulb:** ESP24_SHRGB_01, firmware 1.36.1, MAC `444f8e3136ba`, homeId `19223990`
**Chip:** ESP32-C3 (RISC-V RV32IMC) — despite the ESP24 marketing name. Confirmed via esptool on stock firmware.
**IP:** 10.1.7.59, **UDP port:** 38899

## Architecture

- **wiz.yaml** — ESPHome replacement firmware config for ESP32-C6 board with BP5758D LED driver (5 RGBWW channels).
- **secrets.yaml** — Wi-Fi credentials (`!secret`). **Not committed.**
- **tools/wiz_udp.py** — Python UDP control CLI. Zero dependencies (stdlib only). Supports getPilot, setPilot, setState, setEffect, software fade ramping. Run with `python3 tools/wiz_udp.py <command>`.
- **mqtt/** — Local MQTT broker setup to intercept the bulb's cloud connection and unlock setUserConfig, setFavs, updateOta.
- **firmware/** — Downloaded stock firmware binaries and analysis scripts for Ghidra reverse engineering.

## Common Commands

```bash
# UDP control (no setup needed, talks directly to bulb)
python3 tools/wiz_udp.py get-pilot
python3 tools/wiz_udp.py set-pilot --on --dimming 50 --temp 3000
python3 tools/wiz_udp.py set-effect --mode preview --duration 10 --cct 4000
python3 tools/wiz_udp.py fade --from-dimming 10 --to-dimming 100 --duration 3 --steps 30

# MQTT intercept (requires DNS redirect + mosquitto)
cd mqtt && bash setup.sh
./mqtt/send_mqtt.sh '{"method":"setUserConfig","params":{"fadeIn":700,"fadeOut":700,"userConfigTs":2}}'

# Firmware analysis
cd firmware && bash download_firmware.sh
bash analyze.sh
esptool image-info ESP24_SHRGB_01_1.36.1.bin

# ESPHome (for replacement firmware)
esphome compile wiz.yaml
esphome run wiz.yaml
```

## Hardware Notes

- BP5758D channels 1–5 map to: Blue, Green, Red, Warm White, Cold White (all at 10mA current).
- Color temperature range: 1500K (warm) to 6500K (cold).
- Dimming below 10 is accepted but visually clamps to 10% (getModelConfig confirms minDimLevel: 10).
- `color_interlock: false` allows RGB and white channels to operate simultaneously.

## Protocol Notes

- **UDP (port 38899):** getPilot, setPilot (instant, no fade), setState, setEffect (preview/pulse), getSystemConfig, getUserConfig, getModelConfig, getDevInfo.
- **MQTT only (requires interception):** setUserConfig (fadeIn/fadeOut/po), setFavs (WizClick favorites), updateOta. Requires incrementing `userConfigTs`/`favConfigTs` each call.
- **MQTT broker:** eu.mqtt.wiz.world:8883 (TLS). Bulb client ID: `444f8e3136ba_19223990`. Command topic: `OP/pro/19223990/devices/444f8e3136ba`.
- **Firmware OTA:** Plain HTTP from firmware.wiz.world. Secure version: 0 (no anti-rollback). The `s1`/`s2` OTA params may not be validated.
- **Key reference:** [pywizlight#155](https://github.com/sbidy/pywizlight/issues/155)
