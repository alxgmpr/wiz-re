#!/usr/bin/env python3
"""Self-check for espimage + patch_firmware on a synthetic image. Run: python3 firmware/test_espimage.py"""

import contextlib
import hashlib
import io
import os
import struct
import tempfile

import patch_firmware
from espimage import dispatch_table, segments

DROM, IROM = 0x3C000000, 0x42000000


def build_image():
    names = b"setUserConfig\0getPilot\0reboot\0\0\0"  # 32 bytes, 4-aligned
    ptr = {n: DROM + names.index(n.encode()) for n in ("setUserConfig", "getPilot", "reboot")}
    table = b"".join(struct.pack("<III", ptr[n], IROM + 0x100, f)
                     for n, f in (("setUserConfig", 0x04), ("getPilot", 0x0606), ("reboot", 0x04)))
    drom = names + table + b"\0" * 4  # scanner stops 12 bytes before the end
    irom = b"\x13" * 64
    img = bytearray(b"\xe9\x02\x02\x20" + struct.pack("<I", IROM) + b"\0" * 16)
    for va, seg in ((DROM, drom), (IROM, irom)):
        img += struct.pack("<II", va, len(seg)) + seg
    img += b"\0" * ((15 - len(img)) % 16 + 1 + 32)  # pad + checksum byte + hash
    return img


def main():
    img = build_image()
    assert [va for _, va, _ in segments(img)] == [DROM, IROM]
    assert [(n, f) for _, n, _, f in dispatch_table(img)] == \
        [("setUserConfig", 0x04), ("getPilot", 0x0606), ("reboot", 0x04)]

    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "fw.bin")
        with open(src, "wb") as f:
            f.write(img)
        with contextlib.redirect_stdout(io.StringIO()):
            patch_firmware.patch(src)
        with open(os.path.join(d, "fw.patched.bin"), "rb") as f:
            out = f.read()

    flags = {n: f for _, n, _, f in dispatch_table(out)}
    assert flags == {"setUserConfig": 0x0606, "getPilot": 0x0606, "reboot": 0x0606}, flags

    pos = patch_firmware.checksum_pos(out)
    xor = 0xEF
    for start, _, n in segments(out):
        for b in out[start:start + n]:
            xor ^= b
    assert out[pos] == xor
    assert out[pos + 1:pos + 33] == hashlib.sha256(out[:pos + 1]).digest()
    print("ok")


if __name__ == "__main__":
    main()
