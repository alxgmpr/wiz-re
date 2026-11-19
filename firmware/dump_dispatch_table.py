#!/usr/bin/env python3
"""Dump the complete method dispatch table from Wiz firmware.

Shows: method name, handler address, access flags, and whether UDP or MQTT-only.
"""

import struct
import sys

from espimage import dispatch_table, segments


def dump(path):
    with open(path, 'rb') as f:
        data = f.read()

    entry_addr = struct.unpack_from('<I', data, 4)[0]
    drom_data_start, drom_vaddr, drom_len = segments(data)[0]
    entries = dispatch_table(data)

    # Deduplicate by (name, handler)
    seen = set()
    unique = []
    for off, name, handler, flags in entries:
        key = (name, handler)
        if key not in seen:
            seen.add(key)
            unique.append((off, name, handler, flags))

    # Sort by name
    unique.sort(key=lambda x: x[1])

    print(f"Firmware: {path}")
    print(f"DROM: vaddr=0x{drom_vaddr:08x}, len={drom_len}, file_offset=0x{drom_data_start:06x}")
    print(f"Entry point: 0x{entry_addr:08x}")
    print(f"\n{'Method':<30s} {'Handler':>12s} {'Flags':>12s} {'Access':<20s}")
    print(f"{'-'*30} {'-'*12} {'-'*12} {'-'*20}")

    for _, name, handler, flags in unique:
        b0 = flags & 0xFF
        b1 = (flags >> 8) & 0xFF

        if b1 == 0 and b0 != 0:
            access = "MQTT-only"
        elif b1 != 0:
            access = "UDP+MQTT"
        else:
            access = f"unknown(0x{flags:08x})"

        print(f"{name:<30s} 0x{handler:08x} 0x{flags:08x}   {access}")

    print(f"\nTotal: {len(unique)} methods")

    # Group by access
    mqtt_only = [e for e in unique if ((e[3] >> 8) & 0xFF) == 0 and (e[3] & 0xFF) != 0]
    udp = [e for e in unique if ((e[3] >> 8) & 0xFF) != 0]
    print(f"  UDP+MQTT: {len(udp)}")
    print(f"  MQTT-only: {len(mqtt_only)}")
    print("\nMQTT-only methods:")
    for _, name, _, flags in mqtt_only:
        print(f"  {name} (0x{flags:08x})")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <firmware.bin>")
    dump(sys.argv[1])
