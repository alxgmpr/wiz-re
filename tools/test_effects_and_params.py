#!/usr/bin/env python3
"""Deep-dive testing of setEffect, pulse, and undocumented parameters."""

import json
import socket
import time

IP = "10.1.7.59"
PORT = 38899

def send(method, params=None):
    msg = {"method": method, "params": params or {}}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    try:
        sock.sendto(json.dumps(msg).encode(), (IP, PORT))
        data, _ = sock.recvfrom(4096)
        return json.loads(data.decode())
    except socket.timeout:
        return {"_error": "TIMEOUT"}
    except Exception as e:
        return {"_error": str(e)}
    finally:
        sock.close()

def test(label, method, params):
    resp = send(method, params)
    ok = "result" in resp
    print(f"{'OK' if ok else 'ERR':>3s}  {label}")
    print(f"     -> {json.dumps(resp)}")
    time.sleep(0.2)
    return resp

def restore():
    send("setPilot", {"state": True, "temp": 2700, "dimming": 100})
    time.sleep(0.5)

print("=" * 80)
print("SETEFFECT PARAMETER PROBING")
print("=" * 80)

# The firmware strings show mode names: "pulse", "preview", "musicSync", "autobrightness"
# setEffect in wiz_udp.py uses integer mode. Let's try string modes.
test("setEffect string mode=preview", "setEffect", {"mode": "preview", "duration": 5000, "temp": 3000, "dimming": 50})
test("setEffect string mode=pulse", "setEffect", {"mode": "pulse", "duration": 3000, "temp": 4000, "dimming": 80})
test("setEffect string mode=musicSync", "setEffect", {"mode": "musicSync", "duration": 5000})
test("setEffect string mode=autobrightness", "setEffect", {"mode": "autobrightness"})

# Try with params key wrapping (some firmwares use nested structure)
test("setEffect nested effect obj", "setEffect", {"effect": {"mode": 1, "duration": 5000, "temp": 3000}})

# Try the params the existing wiz_udp.py uses (which apparently worked before?)
# Looking at wiz_udp.py: mode, duration, cct, color, dimming, sceneId, speed
test("setEffect mode=1 dur+cct", "setEffect", {"mode": 1, "duration": 5000, "cct": 3000, "dimming": 50})
test("setEffect mode=2 dur+cct", "setEffect", {"mode": 2, "duration": 5000, "cct": 3000, "dimming": 50})

# Try with "state" wrapper like getPilot returns
test("setEffect with state=true", "setEffect", {"state": True, "mode": 1, "duration": 5000})

# Try integer params matching firmware string names
# "sceneId", "speed", "temp", "dimming" are all nearby in DROM
test("setEffect sceneId+speed", "setEffect", {"sceneId": 4, "speed": 50, "duration": 5000})
test("setEffect temp+dimming+dur", "setEffect", {"temp": 3000, "dimming": 50, "duration": 5000})

# Maybe duration needs to be in different units?
test("setEffect dur=5 (seconds?)", "setEffect", {"mode": 1, "duration": 5})
test("setEffect dur=50 (tenths?)", "setEffect", {"mode": 1, "duration": 50})

# Try with "id" parameter
test("setEffect with id", "setEffect", {"id": 1, "mode": 1, "duration": 5000})

restore()

print("\n" + "=" * 80)
print("PULSE PARAMETER PROBING")
print("=" * 80)

test("pulse delta=-30 dur=1500", "pulse", {"delta": -30, "duration": 1500})
time.sleep(2)
test("pulse delta=30 dur=1500", "pulse", {"delta": 30, "duration": 1500})
time.sleep(2)
test("pulse delta=-100 dur=2000", "pulse", {"delta": -100, "duration": 2000})
time.sleep(2)
test("pulse with temp", "pulse", {"delta": -50, "duration": 2000, "temp": 6500})
time.sleep(2)
test("pulse with sceneId", "pulse", {"delta": -50, "duration": 2000, "sceneId": 4})
time.sleep(2)
test("pulse with speed", "pulse", {"delta": -50, "duration": 2000, "speed": 10})
time.sleep(2)
test("pulse with count", "pulse", {"delta": -50, "duration": 1000, "count": 3})
time.sleep(2)
test("pulse with repeat", "pulse", {"delta": -50, "duration": 1000, "repeat": 3})
time.sleep(2)

restore()

print("\n" + "=" * 80)
print("REGISTRATION PARAMETER PROBING")
print("=" * 80)

# The Wiz app sends registration to discover/register with bulbs
test("registration phoneMac", "registration", {"phoneMac": "aabbccddeeff", "register": True, "phoneIp": "10.1.7.1", "id": "1"})
test("registration homeId", "registration", {"homeId": 19223990, "id": "1", "register": True, "phoneMac": "aabbccddeeff", "phoneIp": "10.1.7.1"})

print("\n" + "=" * 80)
print("SETSCENARIO PARAMETER PROBING")
print("=" * 80)

# getScenario returned: scnrId, confTs, trig, idle, action, actionDur
test("setScenario basic", "setScenario", {"scnrId": 1, "trig": 1, "confTs": 1})
test("setScenario with idle+action", "setScenario", {
    "scnrId": 1, "confTs": 1, "trig": 1,
    "idle": [1, 0, 0, 0, 0, [0, 0, 0, 0, 0], 0, 0],
    "action": [1, 100, 2700, 0, 0, [0, 0, 0, 0, 0], 0, 0],
    "actionDur": 300
})

print("\n" + "=" * 80)
print("SETWIFIBEACONING / SETWIFIPROCESSING PROBING")
print("=" * 80)

# getWifiBeaconing returned: {"enable": 0}
# getWifiProcessing returned: {"beaconMac": "000000000000", "windowSize": 30, "stepSize": 15, "sensitivity": 40}
test("setWifiBeaconing enable=1", "setWifiBeaconing", {"enable": 1})
test("setWifiProcessing", "setWifiProcessing", {"beaconMac": "000000000000", "windowSize": 30, "stepSize": 15, "sensitivity": 40})

print("\n" + "=" * 80)
print("SETCCTABLE PROBING")
print("=" * 80)

# Try to modify the CCT table
test("setCctTable single point", "setCctTable", {"cctPoints": [[2700, 0, 0, 0, 255, 100]], "confTs": 1748148750})

print("\n" + "=" * 80)
print("ADDITIONAL UNDOCUMENTED PARAMS IN SETPILOT")
print("=" * 80)

# Test params found in DROM strings
test("setPilot with schdPsetId", "setPilot", {"state": True, "temp": 2700, "dimming": 100, "schdPsetId": 1})
test("setPilot with ratio=0", "setPilot", {"state": True, "temp": 2700, "dimming": 100, "ratio": 0})
test("setPilot with ratio=100", "setPilot", {"state": True, "temp": 2700, "dimming": 100, "ratio": 100})
test("setPilot with speed=0", "setPilot", {"state": True, "temp": 2700, "dimming": 100, "speed": 0})
test("setPilot with speed=100", "setPilot", {"state": True, "temp": 2700, "dimming": 100, "speed": 100})
test("setPilot w+c channels", "setPilot", {"state": True, "w": 255, "c": 0})
test("setPilot w+c mixed", "setPilot", {"state": True, "w": 128, "c": 128})
test("setPilot w+c+rgb", "setPilot", {"state": True, "r": 100, "g": 50, "b": 200, "w": 50, "c": 50})
test("setPilot cnx=0", "setPilot", {"state": True, "temp": 2700, "dimming": 100, "cnx": 0})
test("setPilot cnx=2", "setPilot", {"state": True, "temp": 2700, "dimming": 100, "cnx": 2})

# Per-command fade
test("setPilot fadeIn=2000", "setPilot", {"state": True, "temp": 2700, "dimming": 100, "fadeIn": 2000})
time.sleep(3)
test("setPilot fadeOut=2000 off", "setPilot", {"state": False, "fadeOut": 2000})
time.sleep(3)
test("setPilot fadeIn=3000 on", "setPilot", {"state": True, "temp": 2700, "dimming": 100, "fadeIn": 3000})
time.sleep(4)

# dim param (abbreviated?)
test("setPilot dim=50", "setPilot", {"state": True, "dim": 50, "temp": 2700})
# spd param
test("setPilot spd=50", "setPilot", {"state": True, "spd": 50, "temp": 2700, "dimming": 100})
# pc param
test("setPilot pc=1", "setPilot", {"state": True, "pc": 1, "temp": 2700, "dimming": 100})

restore()

print("\n" + "=" * 80)
print("GETSENSOR WITH PARAMS")
print("=" * 80)

# getSensor returned "Invalid params" - maybe needs a sensor type?
test("getSensor type=0", "getSensor", {"type": 0})
test("getSensor type=1", "getSensor", {"type": 1})
test("getSensor type=lux", "getSensor", {"type": "lux"})
test("getSensor id=0", "getSensor", {"id": 0})
test("getSensor sensorId=0", "getSensor", {"sensorId": 0})

print("\n" + "=" * 80)
print("SETSTATE PROBING")
print("=" * 80)

# setState returned "Invalid Request" with empty params - needs some params
test("setState dimming=50", "setState", {"dimming": 50})
test("setState temp=3000", "setState", {"temp": 3000, "dimming": 80})
test("setState state=true", "setState", {"state": True, "temp": 2700, "dimming": 100})
test("setState state=false", "setState", {"state": False})

restore()

print("\n" + "=" * 80)
print("RESET PROBING")
print("=" * 80)
# Be careful - just probe what params it wants, don't actually reset
test("reset type=wifi", "reset", {"type": "wifi"})
test("reset with key", "reset", {"resetKey": "test"})

print("\nDone. Bulb restored to 2700K/100%.")
