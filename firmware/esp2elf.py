#!/usr/bin/env python3
"""Convert ESP32 OTA firmware images to ELF files for Ghidra/Binary Ninja.

Parses the ESP-IDF image header, extracts segments, and writes a minimal
ELF32 little-endian RISC-V binary with proper load addresses.
"""

import os
import struct
import sys

from espimage import segments

ESP_IMAGE_MAGIC = 0xE9

# ELF constants
EI_NIDENT = 16
ET_EXEC = 2
EM_RISCV = 243
PT_LOAD = 1
PF_R = 4
PF_W = 2
PF_X = 1


def parse_esp_image(data):
    """Parse ESP-IDF image, return (entry_addr, [(load_addr, segment_data), ...])."""
    if data[0] != ESP_IMAGE_MAGIC:
        raise ValueError(f"Bad magic: 0x{data[0]:02x}, expected 0xE9")
    entry_addr = struct.unpack_from('<I', data, 4)[0]
    return entry_addr, [(va, data[start:start + n]) for start, va, n in segments(data)]


def segments_to_flags(load_addr):
    """Guess segment permissions from load address ranges."""
    if 0x3C000000 <= load_addr < 0x3D000000:  # DROM (data flash mapped)
        return PF_R
    elif 0x3FC00000 <= load_addr < 0x3FD00000:  # DRAM
        return PF_R | PF_W
    elif 0x40380000 <= load_addr < 0x40400000:  # IRAM
        return PF_R | PF_X
    elif 0x42000000 <= load_addr < 0x43000000:  # IROM (instruction flash mapped)
        return PF_R | PF_X
    elif 0x50000000 <= load_addr < 0x50010000:  # RTC memory
        return PF_R | PF_W
    else:
        return PF_R | PF_W | PF_X


def write_elf(entry_addr, segments, outpath):
    """Write a minimal ELF32 LE RISC-V executable."""
    ehdr_size = 52
    phdr_size = 32
    num_phdrs = len(segments)

    # Program headers start right after ELF header
    phdr_offset = ehdr_size
    # Segment data starts after all program headers
    data_offset = ehdr_size + phdr_size * num_phdrs

    # Build program headers and collect data
    phdrs = b''
    seg_data_all = b''
    current_offset = data_offset

    for load_addr, seg_data in segments:
        seg_len = len(seg_data)
        flags = segments_to_flags(load_addr)
        # PT_LOAD: type, offset, vaddr, paddr, filesz, memsz, flags, align
        phdrs += struct.pack('<IIIIIIII',
            PT_LOAD,        # p_type
            current_offset, # p_offset
            load_addr,      # p_vaddr
            load_addr,      # p_paddr
            seg_len,        # p_filesz
            seg_len,        # p_memsz
            flags,          # p_flags
            0x10,           # p_align
        )
        seg_data_all += seg_data
        current_offset += seg_len

    # ELF header
    e_ident = bytes([
        0x7F, ord('E'), ord('L'), ord('F'),  # magic
        1,  # EI_CLASS: ELFCLASS32
        1,  # EI_DATA: ELFDATA2LSB
        1,  # EI_VERSION: EV_CURRENT
        0,  # EI_OSABI: ELFOSABI_NONE
    ]) + b'\x00' * 8  # padding

    ehdr = e_ident + struct.pack('<HHIIIIIHHHHHH',
        ET_EXEC,        # e_type
        EM_RISCV,       # e_machine
        1,              # e_version
        entry_addr,     # e_entry
        phdr_offset,    # e_phoff
        0,              # e_shoff (no section headers)
        0,              # e_flags
        ehdr_size,      # e_ehsize
        phdr_size,      # e_phentsize
        num_phdrs,      # e_phnum
        0,              # e_shentsize
        0,              # e_shnum
        0,              # e_shstrndx
    )

    with open(outpath, 'wb') as f:
        f.write(ehdr)
        f.write(phdrs)
        f.write(seg_data_all)

    print(f"  Wrote {outpath} ({os.path.getsize(outpath)} bytes, {num_phdrs} segments)")


def convert(inpath):
    """Convert an ESP32 firmware .bin to .elf."""
    outpath = inpath.rsplit('.', 1)[0] + '.elf'
    with open(inpath, 'rb') as f:
        data = f.read()

    entry_addr, segments = parse_esp_image(data)
    print(f"{os.path.basename(inpath)}:")
    print(f"  Entry: 0x{entry_addr:08x}, {len(segments)} segments")
    for load_addr, seg_data in segments:
        flags = segments_to_flags(load_addr)
        rwx = ('r' if flags & PF_R else '-') + ('w' if flags & PF_W else '-') + ('x' if flags & PF_X else '-')
        print(f"    0x{load_addr:08x}  {len(seg_data):8d} bytes  {rwx}")

    write_elf(entry_addr, segments, outpath)
    return outpath


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <firmware.bin> [firmware2.bin ...]")
        sys.exit(1)

    for path in sys.argv[1:]:
        try:
            convert(path)
        except Exception as e:
            print(f"ERROR: {path}: {e}")
