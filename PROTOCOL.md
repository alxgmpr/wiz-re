# Wiz Bulb Protocol — Complete Method & Parameter Reference

Firmware reverse engineering results for **ESP24_SHRGB_01** (ESP32-C3 RV32IMC).
Tested on firmware 1.30.1 running on bulb, analyzed against 1.36.1 binary in Binary Ninja.

## Dispatch Table Architecture

Each method in the DROM dispatch table has: `[name_ptr, handler_ptr, flags]` (12 bytes).

**Flag byte meanings:**
- `byte0`: access type (0x04 = cloud/MQTT, 0x06 = local/UDP)
- `byte1`: 0x00 = MQTT-only, non-zero = UDP-accessible
- `byte2`: additional flags (0x02 = broadcast-capable)

**Error codes:**
- `-32601 "Method not found"` — method exists in firmware but disabled for this hardware
- `-32600 "Invalid Request"` — method is MQTT-only (access denied over UDP)
- `-32602 "Invalid params"` — method accessible, but wrong parameters

---

## Complete Method Catalog (74 methods in 1.36.1)

### UDP-Accessible Methods (35)

#### Light Control
| Method | Description | Key Parameters |
|--------|-------------|----------------|
| `setPilot` | Set light state (turns on) | `state`, `dimming`, `temp`, `r/g/b/w/c`, `sceneId`, `speed`, `ratio`, `fadeIn`, `fadeOut`, `cnx`, `schdPsetId`, `dim`, `spd`, `pc` |
| `setState` | Set light state (does NOT auto-turn-on) | Same as setPilot |
| `getPilot` | Query current state | — |
| `setEffect` | Trigger lighting effects | **Nested object** — see Effect System below |
| `getEffect` | Query current effect state | — |
| `pulse` | Brightness pulse | `delta` (brightness change), `duration` (ms) |

#### Configuration Queries
| Method | Description | Response Keys |
|--------|-------------|---------------|
| `getModelConfig` | Hardware capabilities | `ps`, `pwmFreq`, `pwmRes`, `pwmRange`, `wcr`, `nowc`, `cctRange`, `renderFactor`, `hasCctTable`, `drvIface`, `i2cDrv` |
| `getUserConfig` | User settings | `fadeIn`, `fadeOut`, `dftDim`, `opMode`, `po`, `minDimming`, `tapSensor` |
| `getSystemConfig` | System info | `mac`, `homeId`, `roomId`, `rgn`, `moduleName`, `fwVersion`, `groupId`, `ping` |
| `getDevInfo` | Device info | `mac`, `devMac`, `moduleName` |
| `getCctTable` | Full CCT-to-RGBWC mapping | `confTs`, `cctPoints` (14-point table), `maxCctPower` |
| `getFavs` | WizClick favorites | `favs` (4 favorites), `opts` |
| `getAcc` | Accelerometer data | `accs` |
| `getTime` | Current UTC time | `utc` |
| `getPower` | Power consumption | `power` |
| `getTelemetry` | Telemetry data | (returns -32601 on this hardware) |
| `getScenario` | Automation config | `scnrId`, `confTs`, `trig`, `idle`, `action`, `actionDur` |
| `getWifiBeaconing` | WiFi beacon config | `enable` |
| `getWifiProcessing` | WiFi sensing config | `beaconMac`, `windowSize`, `stepSize`, `sensitivity` |
| `getColorProfile` | Color profile | (returns -32601 on this hardware) |
| `getLuxSensing` | Lux sensor config | (returns -32601 on this hardware) |
| `getSensorConfig` | Sensor config | (returns -32601 on this hardware) |
| `getPowerProfile` | Power profile | (returns -32601 on this hardware) |
| `getIotpOTAStatus` | IoTP OTA status | (returns -32601 on this hardware) |
| `getSensor` | Sensor data | (needs specific params — likely requires sensor hardware) |

#### Network & Registration
| Method | Description | Parameters |
|--------|-------------|------------|
| `registration` | App registers with bulb | `phoneMac`, `register`, `phoneIp`, `id` → returns `{mac, success}` |
| `reset` | Factory reset | (flags 0x0404, requires specific params) |
| `syncBroadcastPilot` | Broadcast pilot state | (no response — broadcast only) |
| `syncScnrEvt` | Sync scenario event | — |
| `syncAccEvt` | Sync accelerometer event | — |
| `camSelfTest` | Camera self-test | (returns -32601) |
| `setTest` | Test mode | (returns -32601) |
| `setSensing` | WiFi sensing toggle | (1.30.1 only) |

### MQTT-Only Methods (37)

| Method | Description |
|--------|-------------|
| `setUserConfig` | Set fade times, defaults, power-on behavior |
| `setFavs` | Set WizClick favorites |
| `updateOta` | Trigger firmware OTA update |
| `setWiZClick` | Configure WizClick button |
| `reboot` | Reboot bulb |
| `setModelConfig` | Override model configuration |
| `setSystemConfig` | Set system config |
| `setSensor` | Configure sensor |
| `setSchd` | Set schedule |
| `setSchdPset` | Set schedule preset |
| `setCctTable` | Override CCT-to-channel mapping |
| `setColorProfile` | Set color profile |
| `setWifi` | Set WiFi config |
| `setDevInfo` | Set device info |
| `setSecurity` | Set security level |
| `setAccDisc` | Set accelerometer discovery |
| `setPairingAssist` | Pairing assistant mode |
| `setWifiBeaconing` | Enable/disable WiFi beaconing |
| `setWifiProcessing` | Configure WiFi sensing |
| `setScenario` | Configure automation scenarios |
| `setCommissioning` | Matter commissioning |
| `setSensorConfig` | Configure sensors |
| `setPowerProfile` | Set power profile |
| `setSyncboxListener` | Philips Hue Sync Box listener |
| `setExtendedLightMode` | Extended light modes |
| `setLuxSensing` | Lux sensing config |
| `spaceSenseChecking` | Space sense WiFi presence |
| `spaceSenseTelemetry` | Space sense telemetry |
| `syncInit` | Initialize sync |
| `syncPilot` | Sync pilot state |
| `syncAmbience` | Sync ambience |
| `firstBeat` | First heartbeat to cloud |
| `ping` | Cloud keepalive |
| `matterUpdate` | Matter protocol update |
| `regLight` | Register light with cloud |
| `applyUpdate` | Apply pending update |
| `setAcc` | Set accelerometer config |

---

## Effect System (setEffect)

**Critical discovery**: setEffect uses **nested object keys** as mode selectors, NOT flat `mode` params.

### Correct Format
```json
{"method": "setEffect", "params": {"preview": {"state": 1, "duration": 5, "cct": 3000}}}
```

### Modes

#### `preview` — Preview a light state temporarily
```json
{"preview": {
    "state": 1,           // required: 1=start, 0=stop
    "duration": 5,        // seconds (internally × 1000 for ms)
    "cct": 3000,          // color temperature (1000-12000K)
    "sceneId": 4,         // OR use scene ID (1-35) + speed
    "speed": 50,          // scene animation speed (1-100, default 100)
    "color": [R,G,B,W,C], // OR use 5-channel RGBWC array
    "dimming": 50,        // brightness (10-100)
    "dimRange": [10, 100],// [min, max] brightness range
    "stepTime": [a,b,c,d],// 4-element step timing array
    "pulseCount": 3,      // number of repetitions
    "elm": [...]          // element array for scene programming
}}
```

#### `pulse` — Pulsing effect
Same parameters as `preview`, plus duration and visual pulse behavior.

#### `stepOff` — Delayed turn-off
```json
{"stepOff": {
    "state": 1,
    "duration": 5000,     // raw milliseconds (NOT × 1000)
    "cct": 6500,          // optional: set CCT before timer starts
    "sceneId": 4          // optional: set scene before timer starts
}}
```

#### `autobrightness` — Ambient light tracking
```json
{"autobrightness": {
    "state": 1,
    "luxTarget": 300      // target lux level
}}
```
Requires embedded lux sensor hardware (`embLuxSnr`). Returns -32600 on this bulb.

#### `ambienceSync` — Music/ambience sync
```json
{"ambienceSync": {
    "type": "musicSync",
    "state": 1,
    "syncAreaId": 1
}}
```
Requires external sync source (microphone or Hue Sync Box). Returns -32602 on this bulb.

#### `elm` — Scene element programming
The `elm` key within any mode accepts an array of scene elements:
```json
{"preview": {"state": 1, "duration": 10, "elm": [
    {"cct": 2700},
    {"cct": 6500},
    {"sceneId": 4, "speed": 50}
]}}
```
This cycles between the defined elements during the effect.

#### `orig` — Restore original state
Add `"orig": "current"` at the params level to restore the previous state after the effect ends:
```json
{"method": "setEffect", "params": {
    "preview": {"state": 1, "duration": 5, "cct": 6500},
    "orig": "current"
}}
```

---

## setPilot / setState — Full Parameter Reference

### Standard Parameters
| Param | Type | Range | Description |
|-------|------|-------|-------------|
| `state` | bool | true/false | On/off |
| `dimming` | int | 10-100 | Brightness percentage |
| `temp` | int | 1500-6500 | Color temperature (Kelvin) |
| `r` | int | 0-255 | Red channel |
| `g` | int | 0-255 | Green channel |
| `b` | int | 0-255 | Blue channel |
| `sceneId` | int | 1-35 | Dynamic scene ID |

### Undocumented Parameters (confirmed working)
| Param | Type | Description |
|-------|------|-------------|
| `w` | int | Warm white channel (0-255) — bypasses CCT table |
| `c` | int | Cold white channel (0-255) — bypasses CCT table |
| `speed` | int | Scene animation speed (1-100) |
| `ratio` | int | Unknown purpose (accepted 0-100) |
| `cnx` | int | Connection context? (accepted) |
| `schdPsetId` | int | Scheduler preset ID |
| `dim` | int | Abbreviated dimming param |
| `spd` | int | Abbreviated speed param |
| `pc` | int | Unknown (accepted) |

### Fade Control

**setPilot does NOT support per-command fade.** The handler silently ignores `fadeIn`/`fadeOut`
params (accepts them without error but does nothing). Confirmed by decompiling the handler —
these strings are only in the `setUserConfig` parameter descriptor table.

Fade is a **global setting** configured via `setUserConfig` (MQTT-only):
```bash
# Set global 2-second fade via MQTT (requires interception)
WIZ_MAC=<mac> WIZ_HOME_ID=<homeId> ./mqtt/send_mqtt.sh '{"method":"setUserConfig","params":{"fadeIn":2000,"fadeOut":2000,"userConfigTs":N}}'
# N must increment each call (query current with: wiz_udp.py get-user-config)
```
After setting this, ALL setPilot/setState calls will fade smoothly.

**Alternatives for per-transition fading over UDP:**
1. `setEffect` preview mode (snaps to state, holds for duration, then reverts)
2. Software fade ramp: `wiz_udp.py fade --from-dimming 10 --to-dimming 100 --duration 3`

---

## pulse Method (standalone)

Simple brightness pulse independent of setEffect:
```json
{"method": "pulse", "params": {"delta": -50, "duration": 2000}}
```
| Param | Type | Description |
|-------|------|-------------|
| `delta` | int | Brightness change (-100 to +100) |
| `duration` | int | Pulse duration in milliseconds |

---

## Scene IDs (1-35)

| ID | Scene | ID | Scene |
|----|-------|----|-------|
| 1 | Ocean | 19 | Jungle |
| 2 | Romance | 20 | Mojito |
| 3 | Sunset | 21 | Club |
| 4 | Party | 22 | Christmas |
| 5 | Fireplace | 23 | Halloween |
| 6 | Cozy | 24 | Candlelight |
| 7 | Forest | 25 | Golden White |
| 8 | Pastel Colors | 26 | Pulse |
| 9 | Wake Up | 27 | Steampunk |
| 10 | Bedtime | 28 | Diwali |
| 11 | Warm White | 29 | White |
| 12 | Daylight | 30 | Fandango |
| 13 | Cool White | 31 | Baroque |
| 14 | Night Light | 32 | Fall |
| 15 | Focus | 33-35 | Additional scenes |
| 16 | Relax | | |
| 17 | True Colors | | |
| 18 | TV Time | | |

Scene ID 0 and 36+ are rejected. Scene ID range: **1-35**.

---

## CCT Table (14-point RGBWC Mapping)

From `getCctTable` — defines how color temperature maps to the 5 LED channels:

| CCT (K) | R | G | B | W | C |
|---------|---|---|---|---|---|
| 1500 | 255 | 0 | 0 | 65 | 0 |
| 1800 | 255 | 0 | 0 | 160 | 0 |
| 2000 | 225 | 15 | 0 | 255 | 0 |
| 2200 | 180 | 40 | 0 | 255 | 0 |
| 2400 | 80 | 20 | 0 | 255 | 45 |
| 2700 | 35 | 25 | 0 | 255 | 100 |
| 3000 | 10 | 15 | 0 | 255 | 255 |
| 3200 | 0 | 15 | 0 | 195 | 255 |
| 3500 | 0 | 15 | 3 | 100 | 255 |
| 4000 | 0 | 0 | 0 | 0 | 255 |
| 4500 | 0 | 25 | 20 | 15 | 255 |
| 5000 | 0 | 30 | 30 | 0 | 255 |
| 6000 | 0 | 65 | 65 | 0 | 255 |
| 6500 | 0 | 90 | 70 | 0 | 255 |

Modifiable via MQTT `setCctTable` with incrementing `confTs`.

---

## Hardware Configuration (getModelConfig)

```json
{
    "ps": 1,
    "pwmFreq": 200,
    "pwmRes": 11,
    "pwmRange": [0, 100],
    "wcr": 20,
    "nowc": 1,
    "cctRange": [1500, 2200, 4000, 6500],
    "renderFactor": [55, 255, 0, 255, 80, 80, 30, 70, 255, 255],
    "noSmartConf": 0,
    "hasCctTable": 14,
    "drvIface": 4,
    "i2cDrv": [{
        "chip": "BP5758D",
        "addr": 255,
        "freq": 200,
        "curr": [28, 28, 28, 48, 48],
        "output": [3, 2, 1, 4, 5]
    }]
}
```

**Key fields:**
- `cctRange`: [minK, warmDefaultK, coolDefaultK, maxK]
- `curr`: per-channel current in mA units [B, G, R, WW, CW] = [28, 28, 28, 48, 48]
- `output`: channel-to-driver pin mapping [B→3, G→2, R→1, WW→4, CW→5]
- `pwmRange`: [min%, max%] = [0, 100]
- `renderFactor`: 10-byte array for color rendering adjustments

---

## Sub-10% Dimming

`minDimLevel` is enforced at 10 in firmware. Dimming values 1-9 are **rejected** over setPilot.
`getUserConfig` reports `minDimming: 0` but this doesn't override the hardware limit.
The `pwmRange: [0, 100]` from `getModelConfig` suggests the PWM can go to 0, but the application layer clamps at 10.

---

## Cross-Version Feature Evolution

| Version | Methods | New Features |
|---------|---------|-------------|
| **1.21.14** | 41 | Base: getPilot, setPilot, setState, pulse, registration. `reboot` was UDP-accessible. `getWifiConfig`/`setWifiConfig` (later renamed). |
| **1.30.1** | 59 | +setEffect, +getEffect, +getTelemetry, +getCctTable, +Matter support, +WiFi sensing (spaceSense), +setSensing (UDP!), +updateScene. `reboot` locked to MQTT-only. |
| **1.36.1** | 74 | +getColorProfile, +getScenario, +getSensorConfig, +getPowerProfile, +setExtendedLightMode, +setSyncboxListener, +spaceSenseTelemetry, +camSelfTest, +devDebug |
| **1.36.99** | 75 | +setSportsSync (sports-related light sync) |

**Notable changes:**
- `reboot` was UDP-accessible in 1.21.14, locked to MQTT-only by 1.30.1
- `setSensing` existed in 1.30.1 (UDP+MQTT), removed by 1.36.1
- Matter protocol support (`matterUpdate`) added in 1.30.1
- Sports sync (`setSportsSync`) is newest feature in 1.36.99

---

## DROM Parameter Strings (Additional Discoveries)

Found in firmware binary near handler code:
- `fanState`, `fanSpeed`, `fanMode`, `fanRevrs`, `fanIndState` — fan+light combo support
- `luxTarget`, `lux`, `motionDetected` — sensor/occupancy parameters
- `matterPilot` — Matter protocol integration
- `embLuxSnr` — embedded lux sensor flag
- `tvsyncLastLm` — TV sync last luminance
- `ambienceSync`, `syncAreaId` — Hue Sync Box integration
- `rhythmMode` — rhythm/music mode
- `extendedLightModeIds` — extended light mode list
- `blockPairModes` — blocked pairing modes
- `scnrConfig` — scenario configuration
- `apStickiness` — AP connection persistence
- `tapTmr` — tap sensor timer
- `wizclick` — WizClick button handling
- `SC7A22`, `IIS2DLPC`, `DA262` — supported accelerometer chip names
- `P9867A` — LED driver variant
- `beaconInfo`, `wfsconfTs` — WiFi sensing beacon configuration
