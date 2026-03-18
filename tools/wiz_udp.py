#!/usr/bin/env python3
"""
wiz_udp.py — UDP control tool for Wiz smart bulbs.

Communicates with Wiz bulbs via JSON-over-UDP on port 38899.
Uses only Python stdlib (socket, json, argparse, time, os, sys).

Environment variables:
    WIZ_IP   — default bulb IP address (default: 10.1.7.59)
    WIZ_PORT — default bulb UDP port    (default: 38899)
"""

import argparse
import json
import os
import socket
import sys
import time


class WizBulb:
    """Send JSON commands to a Wiz bulb over UDP and receive responses."""

    def __init__(self, ip: str, port: int, timeout: float = 1.0):
        self.ip = ip
        self.port = port
        self.timeout = timeout

    # ------------------------------------------------------------------ core

    def send(self, payload: dict) -> dict | None:
        """Send a JSON payload and return the parsed JSON response (or None on timeout)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        try:
            message = json.dumps(payload).encode("utf-8")
            sock.sendto(message, (self.ip, self.port))
            data, _ = sock.recvfrom(4096)
            return json.loads(data.decode("utf-8"))
        except socket.timeout:
            return None
        finally:
            sock.close()

    # ------------------------------------------------------------ high-level

    def get_pilot(self) -> dict | None:
        return self.send({"method": "getPilot", "params": {}})

    def set_pilot(self, **params) -> dict | None:
        clean = {k: v for k, v in params.items() if v is not None}
        return self.send({"method": "setPilot", "params": clean})

    def set_state(self, **params) -> dict | None:
        clean = {k: v for k, v in params.items() if v is not None}
        return self.send({"method": "setState", "params": clean})

    def get_system_config(self) -> dict | None:
        return self.send({"method": "getSystemConfig", "params": {}})

    def get_user_config(self) -> dict | None:
        return self.send({"method": "getUserConfig", "params": {}})

    def get_model_config(self) -> dict | None:
        return self.send({"method": "getModelConfig", "params": {}})

    def get_dev_info(self) -> dict | None:
        return self.send({"method": "getDevInfo", "params": {}})

    def set_effect(self, **params) -> dict | None:
        clean = {k: v for k, v in params.items() if v is not None}
        return self.send({"method": "setEffect", "params": clean})

    def pulse(self, delta: int, duration: int) -> dict | None:
        return self.send({"method": "pulse", "params": {"delta": delta, "duration": duration}})

    def get_cct_table(self) -> dict | None:
        return self.send({"method": "getCctTable", "params": {}})

    def get_favs(self) -> dict | None:
        return self.send({"method": "getFavs", "params": {}})

    def get_scenario(self) -> dict | None:
        return self.send({"method": "getScenario", "params": {}})

    def get_power(self) -> dict | None:
        return self.send({"method": "getPower", "params": {}})

    def get_time(self) -> dict | None:
        return self.send({"method": "getTime", "params": {}})

    def get_effect(self) -> dict | None:
        return self.send({"method": "getEffect", "params": {}})

    def get_wifi_processing(self) -> dict | None:
        return self.send({"method": "getWifiProcessing", "params": {}})

    def registration(self, phone_ip: str, phone_mac: str = "aabbccddeeff") -> dict | None:
        return self.send({"method": "registration", "params": {
            "phoneMac": phone_mac, "register": True, "phoneIp": phone_ip, "id": "1",
        }})

    def fade(
        self,
        from_dimming: int | None = None,
        to_dimming: int | None = None,
        from_temp: int | None = None,
        to_temp: int | None = None,
        from_rgb: tuple[int, int, int] | None = None,
        to_rgb: tuple[int, int, int] | None = None,
        duration: float = 2.0,
        steps: int = 20,
    ) -> list[dict | None]:
        """Software-ramp by sending multiple setPilot calls over *duration* seconds.

        Supports simultaneous fading of dimming, color temperature, and/or RGB.
        Returns the list of bulb responses (one per step).
        """
        if steps < 2:
            steps = 2
        interval = duration / (steps - 1)
        responses: list[dict | None] = []

        for i in range(steps):
            t = i / (steps - 1)  # 0.0 -> 1.0
            params: dict = {}

            if from_dimming is not None and to_dimming is not None:
                params["dimming"] = int(from_dimming + (to_dimming - from_dimming) * t)

            if from_temp is not None and to_temp is not None:
                params["temp"] = int(from_temp + (to_temp - from_temp) * t)

            if from_rgb is not None and to_rgb is not None:
                params["r"] = int(from_rgb[0] + (to_rgb[0] - from_rgb[0]) * t)
                params["g"] = int(from_rgb[1] + (to_rgb[1] - from_rgb[1]) * t)
                params["b"] = int(from_rgb[2] + (to_rgb[2] - from_rgb[2]) * t)

            if params:
                resp = self.set_pilot(**params)
                responses.append(resp)

            if i < steps - 1:
                time.sleep(interval)

        return responses


# -------------------------------------------------------------------- helpers

def pp(obj):
    """Pretty-print a JSON-serializable object."""
    if obj is None:
        print("(no response — timed out)")
    else:
        print(json.dumps(obj, indent=2))


def parse_rgb(value: str) -> tuple[int, int, int]:
    """Parse an 'R,G,B' string into a 3-tuple of ints."""
    parts = [int(x.strip()) for x in value.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(f"expected 3 comma-separated values, got {len(parts)}")
    for v in parts:
        if not 0 <= v <= 255:
            raise argparse.ArgumentTypeError(f"RGB values must be 0-255, got {v}")
    return (parts[0], parts[1], parts[2])


# ----------------------------------------------------------- CLI sub-commands

def cmd_get_pilot(args, bulb: WizBulb):
    pp(bulb.get_pilot())


def cmd_set_pilot(args, bulb: WizBulb):
    params: dict = {}
    if args.on:
        params["state"] = True
    elif args.off:
        params["state"] = False
    if args.dimming is not None:
        params["dimming"] = args.dimming
    if args.temp is not None:
        params["temp"] = args.temp
    if args.r is not None:
        params["r"] = args.r
    if args.g is not None:
        params["g"] = args.g
    if args.b is not None:
        params["b"] = args.b
    if args.w is not None:
        params["w"] = args.w
    if args.c is not None:
        params["c"] = args.c
    if args.scene is not None:
        params["sceneId"] = args.scene
    if args.speed is not None:
        params["speed"] = args.speed
    pp(bulb.set_pilot(**params))


def cmd_set_state(args, bulb: WizBulb):
    params: dict = {}
    if args.on:
        params["state"] = True
    elif args.off:
        params["state"] = False
    if args.dimming is not None:
        params["dimming"] = args.dimming
    if args.temp is not None:
        params["temp"] = args.temp
    if args.r is not None:
        params["r"] = args.r
    if args.g is not None:
        params["g"] = args.g
    if args.b is not None:
        params["b"] = args.b
    if args.w is not None:
        params["w"] = args.w
    if args.c is not None:
        params["c"] = args.c
    if args.scene is not None:
        params["sceneId"] = args.scene
    if args.speed is not None:
        params["speed"] = args.speed
    pp(bulb.set_state(**params))


def cmd_get_system_config(args, bulb: WizBulb):
    pp(bulb.get_system_config())


def cmd_get_user_config(args, bulb: WizBulb):
    pp(bulb.get_user_config())


def cmd_get_model_config(args, bulb: WizBulb):
    pp(bulb.get_model_config())


def cmd_get_dev_info(args, bulb: WizBulb):
    pp(bulb.get_dev_info())


def cmd_set_effect(args, bulb: WizBulb):
    # setEffect expects nested objects: {"preview": {...}}, {"pulse": {...}}, {"stepOff": {...}}
    mode = args.mode or "preview"
    if args.stop:
        pp(bulb.set_effect(**{mode: {"state": 0}}))
        return
    inner: dict = {"state": 1}
    if args.duration is not None:
        inner["duration"] = args.duration
    if args.cct is not None:
        inner["cct"] = args.cct
    if args.color is not None:
        parts = [int(x.strip()) for x in args.color.split(",")]
        inner["color"] = parts
    if args.dimming is not None:
        inner["dimming"] = args.dimming
    if args.scene_id is not None:
        inner["sceneId"] = args.scene_id
    if args.speed is not None:
        inner["speed"] = args.speed
    if args.pulse_count is not None:
        inner["pulseCount"] = args.pulse_count
    if args.dim_range is not None:
        parts = [int(x.strip()) for x in args.dim_range.split(",")]
        inner["dimRange"] = parts
    params = {mode: inner}
    if args.restore:
        params["orig"] = "current"
    pp(bulb.set_effect(**params))


def cmd_pulse(args, bulb: WizBulb):
    pp(bulb.pulse(delta=args.delta, duration=args.duration))


def cmd_get_cct_table(args, bulb: WizBulb):
    pp(bulb.get_cct_table())


def cmd_get_favs(args, bulb: WizBulb):
    pp(bulb.get_favs())


def cmd_get_scenario(args, bulb: WizBulb):
    pp(bulb.get_scenario())


def cmd_get_power(args, bulb: WizBulb):
    pp(bulb.get_power())


def cmd_get_time(args, bulb: WizBulb):
    pp(bulb.get_time())


def cmd_get_effect(args, bulb: WizBulb):
    pp(bulb.get_effect())


def cmd_get_wifi_processing(args, bulb: WizBulb):
    pp(bulb.get_wifi_processing())


def cmd_registration(args, bulb: WizBulb):
    pp(bulb.registration(phone_ip=args.phone_ip))


def cmd_raw(args, bulb: WizBulb):
    payload = json.loads(args.json)
    pp(bulb.send(payload))


def cmd_fade(args, bulb: WizBulb):
    from_rgb = parse_rgb(args.from_rgb) if args.from_rgb else None
    to_rgb = parse_rgb(args.to_rgb) if args.to_rgb else None

    print(f"Fading over {args.duration}s in {args.steps} steps ...")
    responses = bulb.fade(
        from_dimming=args.from_dimming,
        to_dimming=args.to_dimming,
        from_temp=args.from_temp,
        to_temp=args.to_temp,
        from_rgb=from_rgb,
        to_rgb=to_rgb,
        duration=args.duration,
        steps=args.steps,
    )
    print(f"Completed {len(responses)} step(s). Last response:")
    if responses:
        pp(responses[-1])
    else:
        print("(no steps executed — check your arguments)")


# --------------------------------------------------------------- shared flags

def add_pilot_flags(parser: argparse.ArgumentParser):
    """Add the common --on/--off, --dimming, --temp, --r/--g/--b, --w/--c, --scene, --fade flags."""
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--on", action="store_true", help="turn the bulb on")
    grp.add_argument("--off", action="store_true", help="turn the bulb off")
    parser.add_argument("--dimming", type=int, metavar="N", help="brightness 10-100")
    parser.add_argument("--temp", type=int, metavar="K", help="color temperature in Kelvin")
    parser.add_argument("--r", type=int, metavar="V", help="red channel 0-255")
    parser.add_argument("--g", type=int, metavar="V", help="green channel 0-255")
    parser.add_argument("--b", type=int, metavar="V", help="blue channel 0-255")
    parser.add_argument("--w", type=int, metavar="V", help="warm white channel 0-255 (bypasses CCT)")
    parser.add_argument("--c", type=int, metavar="V", help="cold white channel 0-255 (bypasses CCT)")
    parser.add_argument("--scene", type=int, metavar="ID", help="scene ID (1-35)")
    parser.add_argument("--speed", type=int, metavar="N", help="scene animation speed 1-100")


# --------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    default_ip = os.environ.get("WIZ_IP", "10.1.7.59")
    default_port = int(os.environ.get("WIZ_PORT", "38899"))

    parser = argparse.ArgumentParser(
        description="Control Wiz smart bulbs over UDP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "environment variables:\n"
            "  WIZ_IP    default bulb IP   (current: %(ip)s)\n"
            "  WIZ_PORT  default bulb port (current: %(port)s)\n"
        )
        % {"ip": default_ip, "port": default_port},
    )
    parser.add_argument("--ip", default=default_ip, help="bulb IP address")
    parser.add_argument("--port", type=int, default=default_port, help="bulb UDP port")
    parser.add_argument("--timeout", type=float, default=1.0, help="UDP response timeout in seconds")

    subs = parser.add_subparsers(dest="command", required=True)

    # get-pilot
    sp = subs.add_parser("get-pilot", help="query current bulb state")
    sp.set_defaults(func=cmd_get_pilot)

    # set-pilot
    sp = subs.add_parser("set-pilot", help="set bulb state (turns bulb on)")
    add_pilot_flags(sp)
    sp.set_defaults(func=cmd_set_pilot)

    # set-state
    sp = subs.add_parser("set-state", help="set bulb state (does not turn on)")
    add_pilot_flags(sp)
    sp.set_defaults(func=cmd_set_state)

    # get-system-config
    sp = subs.add_parser("get-system-config", help="query system configuration")
    sp.set_defaults(func=cmd_get_system_config)

    # get-user-config
    sp = subs.add_parser("get-user-config", help="query user configuration")
    sp.set_defaults(func=cmd_get_user_config)

    # get-model-config
    sp = subs.add_parser("get-model-config", help="query model configuration")
    sp.set_defaults(func=cmd_get_model_config)

    # get-dev-info
    sp = subs.add_parser("get-dev-info", help="query device information")
    sp.set_defaults(func=cmd_get_dev_info)

    # set-effect
    sp = subs.add_parser("set-effect", help="trigger a lighting effect")
    sp.add_argument("--mode", choices=["preview", "pulse", "stepOff"], default="preview", help="effect mode")
    sp.add_argument("--stop", action="store_true", help="stop the current effect")
    sp.add_argument("--duration", type=int, metavar="SEC", help="effect duration in seconds (raw ms for stepOff)")
    sp.add_argument("--cct", type=int, metavar="K", help="correlated color temperature (1000-12000)")
    sp.add_argument("--color", metavar="R,G,B,W,C", help="5-channel values as comma-separated ints")
    sp.add_argument("--dimming", type=int, metavar="N", help="brightness 10-100")
    sp.add_argument("--scene-id", type=int, metavar="ID", help="scene ID (1-35)")
    sp.add_argument("--speed", type=int, metavar="N", help="effect speed 1-100")
    sp.add_argument("--pulse-count", type=int, metavar="N", help="number of pulse repetitions")
    sp.add_argument("--dim-range", metavar="MIN,MAX", help="brightness range as min,max")
    sp.add_argument("--restore", action="store_true", help="restore original state after effect")
    sp.set_defaults(func=cmd_set_effect)

    # pulse (standalone method)
    sp = subs.add_parser("pulse", help="brightness pulse (standalone method)")
    sp.add_argument("--delta", type=int, required=True, help="brightness change (-100 to +100)")
    sp.add_argument("--duration", type=int, required=True, help="pulse duration in milliseconds")
    sp.set_defaults(func=cmd_pulse)

    # get-cct-table
    sp = subs.add_parser("get-cct-table", help="query CCT-to-RGBWC channel mapping")
    sp.set_defaults(func=cmd_get_cct_table)

    # get-favs
    sp = subs.add_parser("get-favs", help="query WizClick favorites")
    sp.set_defaults(func=cmd_get_favs)

    # get-scenario
    sp = subs.add_parser("get-scenario", help="query automation scenario config")
    sp.set_defaults(func=cmd_get_scenario)

    # get-power
    sp = subs.add_parser("get-power", help="query power consumption")
    sp.set_defaults(func=cmd_get_power)

    # get-time
    sp = subs.add_parser("get-time", help="query bulb UTC time")
    sp.set_defaults(func=cmd_get_time)

    # get-effect
    sp = subs.add_parser("get-effect", help="query current effect state")
    sp.set_defaults(func=cmd_get_effect)

    # get-wifi-processing
    sp = subs.add_parser("get-wifi-processing", help="query WiFi sensing configuration")
    sp.set_defaults(func=cmd_get_wifi_processing)

    # registration
    sp = subs.add_parser("registration", help="register with bulb (app discovery)")
    sp.add_argument("--phone-ip", default="10.1.7.1", help="phone/controller IP")
    sp.set_defaults(func=cmd_registration)

    # raw
    sp = subs.add_parser("raw", help="send raw JSON payload")
    sp.add_argument("json", help='JSON string, e.g. \'{"method":"getPilot","params":{}}\'')
    sp.set_defaults(func=cmd_raw)

    # fade
    sp = subs.add_parser("fade", help="software fade ramp (dimming, temp, and/or RGB)")
    sp.add_argument("--from-dimming", type=int, metavar="N", help="starting brightness 10-100")
    sp.add_argument("--to-dimming", type=int, metavar="N", help="ending brightness 10-100")
    sp.add_argument("--from-temp", type=int, metavar="K", help="starting color temperature")
    sp.add_argument("--to-temp", type=int, metavar="K", help="ending color temperature")
    sp.add_argument("--from-rgb", metavar="R,G,B", help="starting RGB as comma-separated 0-255")
    sp.add_argument("--to-rgb", metavar="R,G,B", help="ending RGB as comma-separated 0-255")
    sp.add_argument("--duration", type=float, default=2.0, help="ramp duration in seconds (default: 2)")
    sp.add_argument("--steps", type=int, default=20, help="number of steps (default: 20)")
    sp.set_defaults(func=cmd_fade)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    bulb = WizBulb(ip=args.ip, port=args.port, timeout=args.timeout)
    args.func(args, bulb)


if __name__ == "__main__":
    main()
