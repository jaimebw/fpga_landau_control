#!/usr/bin/env python3
# landau_gpio_test.py
# Quick sanity test for: axi_gpio_out (a1, a2+TEST) -> glue -> Landau -> axi_gpio_in (b, status)

import argparse, mmap, os, struct, sys

def parse_int(x): return int(x, 0)

class MMIO:
    def __init__(self, phys, size):
        page = mmap.PAGESIZE
        self.fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        self.base = phys
        self.size = size
        self.page_base = phys & ~(page - 1)
        self.page_off  = phys - self.page_base
        self.mm = mmap.mmap(self.fd, size + self.page_off, mmap.MAP_SHARED,
                            mmap.PROT_READ | mmap.PROT_WRITE, offset=self.page_base)
    def write32(self, off, val):
        off += self.page_off
        self.mm[off:off+4] = struct.pack("<I", val & 0xFFFFFFFF)
    def read32(self, off):
        off += self.page_off
        return struct.unpack("<I", self.mm[off:off+4])[0]
    def close(self):
        self.mm.close()
        os.close(self.fd)

def q16_16_to_float(u32):
    # interpret as signed 32-bit Q16.16
    if u32 & 0x80000000:
        u32 = -((~u32 + 1) & 0xFFFFFFFF)
    return float(u32) / 65536.0

def main():
    ap = argparse.ArgumentParser(description="Test Landau control via AXI-GPIO")
    ap.add_argument("--out-base", default="0x41200000", type=parse_int, help="axi_gpio_out base phys addr")
    ap.add_argument("--in-base",  default="0x41210000", type=parse_int, help="axi_gpio_in base phys addr")
    ap.add_argument("--a1",       default="0x00010000", type=parse_int, help="a1 (Q16.16), default 1.0")
    ap.add_argument("--a2",       default="0x00000000", type=parse_int, help="a2 (Q16.16)")
    ap.add_argument("--test",     default=1, type=int, choices=[0,1],    help="TEST bit (1 passthrough a1+1)")
    ap.add_argument("--size",     default="0x1000", type=parse_int)
    args = ap.parse_args()

    if os.geteuid() != 0:
        print("Run with sudo.", file=sys.stderr); sys.exit(1)

    # AXI GPIO regs: 0x00 DATA ch1, 0x04 TRI ch1, 0x08 DATA ch2, 0x0C TRI ch2
    OUT_DATA1, OUT_TRI1, OUT_DATA2, OUT_TRI2 = 0x00, 0x04, 0x08, 0x0C
    IN_DATA1,  IN_TRI1,  IN_DATA2,  IN_TRI2  = 0x00, 0x04, 0x08, 0x0C

    out = MMIO(args.out_base, args.size)
    _in = MMIO(args.in_base,  args.size)

    try:
        # Directions: out = outputs (0), in = inputs (1)
        out.write32(OUT_TRI1, 0x00000000)
        out.write32(OUT_TRI2, 0x00000000)
        _in.write32(IN_TRI1,  0xFFFFFFFF)
        _in.write32(IN_TRI2,  0xFFFFFFFF)

        # Pack a2 + TEST per your glue (TEST in bit0; a2 in [31:1], LSB cleared)
        a2_test = (args.a2 & 0xFFFFFFFE) | (args.test & 0x1)

        # Drive a1, a2+TEST
        out.write32(OUT_DATA1, args.a1)
        out.write32(OUT_DATA2, a2_test)

        # Read back b and status
        b_raw  = _in.read32(IN_DATA1)
        st_raw = _in.read32(IN_DATA2)

        print(f"axi_gpio_out@0x{args.out_base:X}: a1=0x{args.a1:08X} ({q16_16_to_float(args.a1):.6f}), "
              f"a2+TEST=0x{a2_test:08X} (a2={q16_16_to_float(args.a2):.6f}, TEST={args.test})")
        print(f"axi_gpio_in @0x{args.in_base:X}:  b = 0x{b_raw:08X}  ({q16_16_to_float(b_raw):.6f}), "
              f"status=0x{st_raw:08X} (VALID bit0 should be 1)")

        # If TEST=1 and a1=1.0, expect b ~= 2.0 (0x00020000)
        # If TEST=0 and a1=1.0, a2=0.0, expect b ~= -0.2 (0xFFFFCCCD)
    finally:
        out.close(); _in.close()

if __name__ == "__main__":
    main()
