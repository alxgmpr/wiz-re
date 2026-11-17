"""Shared parsing for ESP-IDF app images (stock Wiz firmware .bin files)."""

import struct

HEADER_LEN = 24  # 8-byte basic header + 16-byte extended header


def segments(data):
    """Return [(data_file_offset, load_addr, length), ...] for each image segment."""
    out = []
    off = HEADER_LEN
    for _ in range(data[1]):
        if off + 8 > len(data):
            break
        load_addr, length = struct.unpack_from('<II', data, off)
        out.append((off + 8, load_addr, length))
        off += 8 + length
    return out


def segments_end(data):
    """File offset just past the last segment's data."""
    start, _, length = segments(data)[-1]
    return start + length


def dispatch_table(data):
    """Scan DROM (segment 0) for method dispatch entries.

    Each entry is [name_ptr, handler_ptr, flags] (12 bytes): name_ptr points into
    DROM, handler_ptr into IROM (0x42xxxxxx), flags is a small value.
    Returns [(file_offset, name, handler, flags), ...].
    """
    drom_start, drom_vaddr, drom_len = segments(data)[0]

    def read_name(va):
        foff = drom_start + (va - drom_vaddr)
        if not drom_start <= foff < drom_start + drom_len:
            return None
        end = data.find(b'\x00', foff, foff + 64)
        if end > foff:
            try:
                return bytes(data[foff:end]).decode('ascii')
            except UnicodeDecodeError:
                pass
        return None

    entries = []
    for off in range(drom_start, drom_start + drom_len - 12, 4):
        w0, w1, w2 = struct.unpack_from('<III', data, off)
        if (drom_vaddr <= w0 < drom_vaddr + drom_len and
                0x42000000 <= w1 < 0x42200000 and
                w2 < 0x00100000):
            name = read_name(w0)
            if name and len(name) > 2 and name.isprintable():
                entries.append((off, name, w1, w2))
    return entries
