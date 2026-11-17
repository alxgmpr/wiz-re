#!/usr/bin/env python3
"""Test every known Wiz bulb method over UDP and dump full responses.

Extracted method catalog from firmware 1.36.1 DROM dispatch table.
"""

import argparse
import json
import os
import time

from wiz_udp import WizBulb

# Skipped unless --dangerous: these can reset, reboot, or reconfigure the bulb
# if accepted (e.g. on firmware patched with firmware/patch_firmware.py).
DANGEROUS = {"reset", "resetCert", "setWifi", "setSecurity", "applyUpdate",
             "setDevInfo", "reboot", "updateOta", "setSystemConfig", "setModelConfig"}


def send(bulb, method, params=None):
    """Send a method call; return the response or an {"_error": ...} dict."""
    try:
        return bulb.call(method, params) or {"_error": "TIMEOUT (no response)"}
    except Exception as e:
        return {"_error": str(e)}


# ── Complete method catalog from 1.36.1 DROM ──
# Organized by category. Each entry: (method_name, params_to_send)

TESTS = [
    # ── GET methods (read-only, safe) ──
    ("getPilot", {}),
    ("getDevInfo", {}),
    ("getSystemConfig", {}),
    ("getUserConfig", {}),
    ("getModelConfig", {}),
    ("getEffect", {}),
    ("getTelemetry", {}),
    ("getFavs", {}),
    ("getSensor", {}),
    ("getLuxSensing", {}),
    ("getAcc", {}),
    ("getTime", {}),
    ("getPower", {}),
    ("getCctTable", {}),
    ("getColorProfile", {}),
    ("getWifiBeaconing", {}),
    ("getWifiProcessing", {}),
    ("getWifiProcessingData", {}),
    ("getScenario", {}),
    ("getSensorConfig", {}),
    ("getPowerProfile", {}),
    ("getIotpOTAStatus", {}),
    ("getTest", {}),

    # ── Other read/info methods ──
    ("registration", {}),
    ("registration", {"phoneIp": "192.0.2.1", "register": True, "phoneOs": "linux", "id": "test"}),
    ("devDebug", {}),
    ("syncBroadcastPilot", {}),
    ("syncScnrEvt", {}),
    ("syncTest", {}),
    ("syncSchdPset", {}),
    ("syncOffset", {}),
    ("syncAmbience", {}),
    ("spaceSenseChecking", {}),
    ("spaceSenseTelemetry", {}),
    ("camSelfTest", {}),
    ("bug", {}),

    # ── SET methods with empty params (probe for error messages showing accepted params) ──
    ("setEffect", {}),
    ("setState", {}),
    ("setExtendedLightMode", {}),
    ("setScenario", {}),
    ("setTest", {}),
    ("setLuxSensing", {}),
    ("setAccDisc", {}),
    ("setPairingAssist", {}),
    ("setWifiBeaconing", {}),
    ("setWifiProcessing", {}),
    ("setSyncboxListener", {}),
    ("setCommissioning", {}),
    ("setSensorConfig", {}),
    ("setPowerProfile", {}),
    ("setCctTable", {}),
    ("setColorProfile", {}),
    ("setSchd", {}),
    ("setSchdPset", {}),
    ("setWifi", {}),
    ("setDevInfo", {}),
    ("applyUpdate", {}),
    ("resetFan", {}),
    ("reset", {}),
    ("resetCert", {}),
    ("setSecurity", {}),

    # ── MQTT-only methods (likely rejected over UDP, but let's see) ──
    ("setUserConfig", {}),
    ("setFavs", {}),
    ("updateOta", {}),
    ("setWiZClick", {}),
    ("reboot", {}),
    ("setModelConfig", {}),
    ("setSensor", {}),
    ("setSystemConfig", {}),

    # ── Probe setEffect with various mode values ──
    ("setEffect", {"mode": 0}),
    ("setEffect", {"mode": 1}),
    ("setEffect", {"mode": 2}),
    ("setEffect", {"mode": 3}),
    ("setEffect", {"mode": 4}),

    # ── Probe setExtendedLightMode with various params ──
    ("setExtendedLightMode", {"mode": 0}),
    ("setExtendedLightMode", {"mode": 1}),
    ("setExtendedLightMode", {"mode": 2}),

    # ── Sub-10% dimming probes ──
    ("setPilot", {"dimming": 1}),
    ("setPilot", {"dimming": 5}),
    ("setPilot", {"dimming": 9}),
    ("setPilot", {"dimming": 10}),
    # Restore after dimming tests
    ("setPilot", {"state": True, "dimming": 50, "temp": 4000}),

    # ── Scene ID probes (test a range) ──
    ("setPilot", {"sceneId": 0}),
    ("setPilot", {"sceneId": 1}),
    ("setPilot", {"sceneId": 2}),
    ("setPilot", {"sceneId": 3}),
    ("setPilot", {"sceneId": 4}),
    ("setPilot", {"sceneId": 5}),
    ("setPilot", {"sceneId": 6}),
    ("setPilot", {"sceneId": 7}),
    ("setPilot", {"sceneId": 8}),
    ("setPilot", {"sceneId": 9}),
    ("setPilot", {"sceneId": 10}),
    ("setPilot", {"sceneId": 11}),
    ("setPilot", {"sceneId": 12}),
    ("setPilot", {"sceneId": 13}),
    ("setPilot", {"sceneId": 14}),
    ("setPilot", {"sceneId": 15}),
    ("setPilot", {"sceneId": 16}),
    ("setPilot", {"sceneId": 17}),
    ("setPilot", {"sceneId": 18}),
    ("setPilot", {"sceneId": 19}),
    ("setPilot", {"sceneId": 20}),
    ("setPilot", {"sceneId": 25}),
    ("setPilot", {"sceneId": 27}),
    ("setPilot", {"sceneId": 28}),
    ("setPilot", {"sceneId": 29}),
    ("setPilot", {"sceneId": 30}),
    ("setPilot", {"sceneId": 31}),
    ("setPilot", {"sceneId": 32}),
    ("setPilot", {"sceneId": 35}),
    ("setPilot", {"sceneId": 100}),
    ("setPilot", {"sceneId": 1000}),
    # Restore
    ("setPilot", {"state": True, "dimming": 50, "temp": 4000}),

    # ── Undocumented setPilot params ──
    ("setPilot", {"state": True, "dimming": 50, "temp": 3000, "speed": 50}),
    ("setPilot", {"state": True, "dimming": 50, "temp": 3000, "ratio": 50}),
    ("setPilot", {"state": True, "r": 255, "g": 0, "b": 0, "w": 100, "c": 0}),
    ("setPilot", {"state": True, "r": 255, "g": 0, "b": 0, "w": 0, "c": 0, "dimming": 100}),
    ("setPilot", {"state": True, "cnx": 1}),
    ("setPilot", {"state": True, "dimming": 50, "temp": 3000, "fadeIn": 1000}),
    ("setPilot", {"state": True, "dimming": 50, "temp": 3000, "fadeOut": 1000}),

    # ── setEffect deeper probes ──
    ("setEffect", {"mode": 1, "duration": 5, "cct": 3000, "dimming": 50}),
    ("setEffect", {"mode": 2, "duration": 5, "cct": 3000, "dimming": 50}),
    ("setEffect", {"mode": 1, "duration": 5, "sceneId": 4}),
    ("setEffect", {"mode": 1, "speed": 50, "duration": 10}),
    ("setEffect", {"mode": 1, "duration": 5, "color": [255, 0, 0, 0, 0]}),

    # Restore bulb to sane state
    ("setPilot", {"state": True, "dimming": 50, "temp": 4000}),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ip", default=os.environ.get("WIZ_IP"), required="WIZ_IP" not in os.environ)
    ap.add_argument("--port", type=int, default=38899)
    ap.add_argument("--dangerous", action="store_true", help=f"also send {', '.join(sorted(DANGEROUS))}")
    args = ap.parse_args()
    bulb = WizBulb(args.ip, args.port, timeout=2.0)
    tests = [t for t in TESTS if args.dangerous or t[0] not in DANGEROUS]

    print(f"Testing {len(tests)} method calls against {args.ip}:{args.port}")
    print(f"{'='*80}\n")

    results = {}
    for i, (method, params) in enumerate(tests):
        resp = send(bulb, method, params)

        is_timeout = "_error" in resp and "TIMEOUT" in resp.get("_error", "")
        is_error = "error" in resp
        has_result = "result" in resp

        if is_timeout:
            status = "TIMEOUT"
        elif is_error:
            status = f"ERROR({resp['error'].get('code', '?')})"
        elif has_result:
            status = "OK"
        else:
            status = "UNKNOWN"

        print(f"[{i+1:3d}/{len(tests)}] {status:12s} {method}")
        if params:
            print(f"{'':16s} params: {json.dumps(params)}")
        print(f"{'':16s} resp:   {json.dumps(resp)}")
        print()

        results.setdefault(method, []).append({
            "params": params,
            "response": resp,
            "status": status,
        })

        time.sleep(0.15)  # don't flood the bulb

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    methods_ok = []
    methods_err = []
    methods_timeout = []

    for method, calls in results.items():
        for call in calls:
            s = call["status"]
            if s == "OK":
                methods_ok.append((method, call))
            elif s == "TIMEOUT":
                methods_timeout.append((method, call))
            else:
                methods_err.append((method, call))

    print(f"OK responses:      {len(methods_ok)}")
    print(f"Error responses:   {len(methods_err)}")
    print(f"Timeouts:          {len(methods_timeout)}")

    print("\n── Methods that returned data ──")
    seen = set()
    for method, call in methods_ok:
        if method not in seen:
            seen.add(method)
            resp = call["response"]
            result = resp.get("result", {})
            if isinstance(result, dict):
                print(f"  {method}: keys={list(result.keys())}")
            else:
                print(f"  {method}: {result}")

    print("\n── Methods that returned errors ──")
    seen = set()
    for method, call in methods_err:
        k = f"{method}|{call['params']}"
        if k not in seen:
            seen.add(k)
            err = call["response"].get("error", {})
            print(f"  {method}({json.dumps(call['params'])}): code={err.get('code')} msg={err.get('message', '')}")

    print("\n── Methods that timed out (possibly MQTT-only) ──")
    seen = set()
    for method, _ in methods_timeout:
        if method not in seen:
            seen.add(method)
            print(f"  {method}")

    # Dump full results to JSON
    outpath = "probe_results.json"
    with open(outpath, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results written to {outpath}")


if __name__ == "__main__":
    main()
