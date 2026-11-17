#!/usr/bin/env python3
"""Patch Wiz firmware to enable MQTT-only methods over UDP.

Modifies the method dispatch table flags so that methods like setUserConfig,
setFavs, updateOta, etc. become accessible over UDP (port 38899) without
needing MQTT interception.

Also recalculates the ESP-IDF image checksum and SHA256 validation hash.

Usage:
    python3 patch_firmware.py ESP24_SHRGB_01_1.36.1.bin
    # Creates ESP24_SHRGB_01_1.36.1.patched.bin
"""

import hashlib
import struct
import sys

from espimage import dispatch_table, segments, segments_end

# Methods to unlock over UDP. Change flags from 0x04 (MQTT-only) to 0x0606 (UDP+MQTT).
# Using 0x0606 to match the pattern used by existing UDP-accessible get methods.
METHODS_TO_UNLOCK = {
    'setUserConfig',
    'setFavs',
    'updateOta',
    'setWiZClick',
    'reboot',
    'setModelConfig',
    'setSensor',
    'setSchd',
}

NEW_FLAGS = 0x00000606  # same as getPilot, getUserConfig, etc.


def checksum_pos(data):
    """Offset of the XOR checksum byte: end of segments, padded so offset % 16 == 15."""
    end = segments_end(data)
    return end + (15 - end) % 16


def checksum(data):
    """ESP-IDF image checksum: XOR of all segment data bytes, seeded with 0xEF."""
    xor = 0xEF
    for start, _, length in segments(data):
        for b in data[start:start + length]:
            xor ^= b
    return xor


def patch(inpath):
    with open(inpath, 'rb') as f:
        data = bytearray(f.read())

    print(f"Loaded {inpath} ({len(data)} bytes)")

    # Find dispatch table
    entries = dispatch_table(data)
    if not entries:
        print("ERROR: Could not find dispatch table!")
        sys.exit(1)

    print(f"Found {len(entries)} dispatch table entries")
    print()

    # Apply patches
    patched = 0
    for off, name, _, flags in entries:
        if name in METHODS_TO_UNLOCK:
            b1 = (flags >> 8) & 0xFF
            if b1 == 0:  # currently MQTT-only
                flags_off = off + 8
                old = struct.unpack_from('<I', data, flags_off)[0]
                struct.pack_into('<I', data, flags_off, NEW_FLAGS)
                print(f"  PATCHED: {name:<24s}  0x{old:08x} -> 0x{NEW_FLAGS:08x}  (bin offset 0x{flags_off:06x})")
                patched += 1
            else:
                print(f"  SKIP:    {name:<24s}  already UDP-accessible (0x{flags:08x})")

    if patched == 0:
        print("\nNo patches needed!")
        return

    print(f"\nPatched {patched} method(s)")

    # Recalculate checksum
    cksum_pos, cksum_val = checksum_pos(data), checksum(data)
    old_cksum = data[cksum_pos]
    data[cksum_pos] = cksum_val
    print(f"Checksum: 0x{old_cksum:02x} -> 0x{cksum_val:02x} (at 0x{cksum_pos:06x})")

    # Recalculate validation hash: SHA256 of everything up to and including the checksum
    hash_off = cksum_pos + 1
    new_hash = hashlib.sha256(data[:hash_off]).digest()
    old_hash = data[hash_off:hash_off + 32].hex()
    data[hash_off:hash_off + 32] = new_hash
    print(f"Image SHA256: {old_hash[:16]}... -> {new_hash.hex()[:16]}... (at 0x{hash_off:06x})")

    # Recalculate signature block hash (covers 0 to sig_start)
    hash_end = hash_off + 32
    sig_start = (hash_end + 0xFFF) & ~0xFFF  # next 0x1000-aligned boundary
    if sig_start + 1216 <= len(data) and data[sig_start] == 0xE7 and data[sig_start + 1] == 0x02:
        sig_hash_off = sig_start + 4
        old_sig_hash = data[sig_hash_off:sig_hash_off + 32].hex()
        new_sig_hash = hashlib.sha256(data[:sig_start]).digest()
        data[sig_hash_off:sig_hash_off + 32] = new_sig_hash
        print(f"Sig block SHA256: {old_sig_hash[:16]}... -> {new_sig_hash.hex()[:16]}... (at 0x{sig_hash_off:06x})")
    else:
        print("No signature block found")

    # Write patched firmware
    outpath = inpath.rsplit('.', 1)[0] + '.patched.bin'
    with open(outpath, 'wb') as f:
        f.write(data)

    print(f"\nWrote {outpath} ({len(data)} bytes)")

    # Verify
    print("\nVerification:")
    verify_entries = dispatch_table(data)
    for _, name, _, flags in verify_entries:
        if name in METHODS_TO_UNLOCK:
            b1 = (flags >> 8) & 0xFF
            status = "UDP OK" if b1 != 0 else "STILL MQTT-ONLY!"
            print(f"  {name:<24s}  0x{flags:08x}  {status}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <firmware.bin>")
        print("Creates <firmware>.patched.bin with MQTT-only methods unlocked over UDP")
        sys.exit(1)

    patch(sys.argv[1])
