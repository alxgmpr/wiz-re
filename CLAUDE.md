# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ESPHome configuration for a **PureSmart TruColor** smart light bulb based on an ESP32-C6 (esp32-c6-devkitm-1) using the ESP-IDF framework. The bulb has RGBWW (Red, Green, Blue, Warm White, Cold White) LEDs driven by a **BP5758D** LED driver IC over a 2-wire interface (data on GPIO1, clock on GPIO0).

## Common Commands

```bash
# Compile the firmware
esphome compile wiz.yaml

# Upload firmware over USB
esphome upload wiz.yaml

# Compile and upload
esphome run wiz.yaml

# Upload over Wi-Fi (OTA) after initial flash
esphome run wiz.yaml --device <IP_ADDRESS>

# View device logs
esphome logs wiz.yaml

# Validate configuration without compiling
esphome config wiz.yaml
```

## Architecture

- **wiz.yaml** — Main ESPHome device configuration: defines the ESP32 board, Wi-Fi, API, OTA, the BP5758D LED driver (5 channels), and an RGBWW light entity exposed to Home Assistant.
- **secrets.yaml** — Wi-Fi credentials referenced via `!secret`. **Do not commit to public repositories.**

## Hardware Notes

- BP5758D channels 1–5 map to: Blue, Green, Red, Warm White, Cold White (all at 10mA current).
- Color temperature range: 1500K (warm) to 6500K (cold).
- `color_interlock: false` allows RGB and white channels to operate simultaneously.
