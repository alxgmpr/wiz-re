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
import os

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


def find_dispatch_table(data):
    """Find and return dispatch table entries as [(offset, name, handler, flags), ...]."""
    # DROM segment: file_offs=0x18, load_addr from header
    # Parse segment 0 to get DROM base address
    seg_count = data[1]
    entry_addr = struct.unpack_from('<I', data, 4)[0]

    offset = 24  # after 24-byte header
    segments = []
    for i in range(seg_count):
        load_addr, seg_len = struct.unpack_from('<II', data, offset)
        segments.append((offset + 8, load_addr, seg_len))  # (data_start, vaddr, length)
        offset += 8 + seg_len

    drom_data_start, drom_vaddr, drom_len = segments[0]

    def read_method_name(va):
        """Read method name from a method descriptor pointer."""
        foff = drom_data_start + (va - drom_vaddr)
        if foff < drom_data_start or foff >= drom_data_start + drom_len:
            return None
        end = data.find(b'\x00', foff, foff + 64)
        if end > foff:
            try:
                return data[foff:end].decode('ascii')
            except (UnicodeDecodeError, ValueError):
                pass
        return None

    # Scan DROM for dispatch table entries:
    # [name_ptr(4), handler_ptr(4), flags(4)] where:
    #   name_ptr is in DROM range
    #   handler_ptr is in IROM range (0x42xxxxxx)
    #   flags is a small value
    entries = []

    # Find all candidate entries across the full DROM
    for off in range(drom_data_start, drom_data_start + drom_len - 12, 4):
        w0, w1, w2 = struct.unpack_from('<III', data, off)
        if (drom_vaddr <= w0 < drom_vaddr + drom_len and
                0x42000000 <= w1 < 0x42200000 and
                w2 < 0x00100000):
            name = read_method_name(w0)
            if name and len(name) > 2 and name.isascii() and name.isprintable():
                entries.append((off, name, w1, w2))

    return entries


def recalculate_checksum(data):
    """Recalculate the ESP-IDF image XOR checksum."""
    # Checksum covers all segment data. It's the XOR of all bytes, stored
    # at the byte just before the validation hash (or at the end if no hash).
    # The checksum byte is at offset (end_of_segments), padded to 16-byte boundary.
    seg_count = data[1]
    offset = 24
    for i in range(seg_count):
        _, seg_len = struct.unpack_from('<II', data, offset)
        offset += 8 + seg_len

    # Checksum position: padded to 16-byte alignment
    checksum_pos = offset
    # Pad to 16-byte boundary
    while checksum_pos % 16 != 15:
        checksum_pos += 1

    # Calculate XOR checksum of all bytes from offset 0 to checksum_pos
    # Actually, ESP-IDF checksum is: XOR of all segment data bytes, seeded with 0xEF
    xor = 0xEF
    off = 24
    for i in range(seg_count):
        _, seg_len = struct.unpack_from('<II', data, off)
        seg_data_start = off + 8
        for b in data[seg_data_start:seg_data_start + seg_len]:
            xor ^= b
        off += 8 + seg_len

    return checksum_pos, xor


def recalculate_hash(data):
    """Recalculate the SHA256 validation hash at the end of the image."""
    # The last 32 bytes of the image are the SHA256 hash of everything before them
    hash_offset = len(data) - 32
    new_hash = hashlib.sha256(data[:hash_offset]).digest()
    return hash_offset, new_hash


def patch(inpath):
    with open(inpath, 'rb') as f:
        data = bytearray(f.read())

    print(f"Loaded {inpath} ({len(data)} bytes)")

    # Find dispatch table
    entries = find_dispatch_table(data)
    if not entries:
        print("ERROR: Could not find dispatch table!")
        sys.exit(1)

    print(f"Found {len(entries)} dispatch table entries")
    print()

    # Apply patches
    patched = 0
    for off, name, handler, flags in entries:
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
    cksum_pos, cksum_val = recalculate_checksum(data)
    old_cksum = data[cksum_pos]
    data[cksum_pos] = cksum_val
    print(f"Checksum: 0x{old_cksum:02x} -> 0x{cksum_val:02x} (at 0x{cksum_pos:06x})")

    # Recalculate validation hash
    hash_off, new_hash = recalculate_hash(data)
    old_hash = data[hash_off:hash_off + 32].hex()
    data[hash_off:hash_off + 32] = new_hash
    print(f"SHA256: {old_hash[:16]}... -> {new_hash.hex()[:16]}...")

    # Write patched firmware
    outpath = inpath.rsplit('.', 1)[0] + '.patched.bin'
    with open(outpath, 'wb') as f:
        f.write(data)

    print(f"\nWrote {outpath} ({len(data)} bytes)")

    # Verify
    print("\nVerification:")
    verify_entries = find_dispatch_table(data)
    for off, name, handler, flags in verify_entries:
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
