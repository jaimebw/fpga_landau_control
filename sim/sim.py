#!/usr/bin/env python3
# sim_axi.py — Landau sim loop that talks to FPGA via AXI-GPIO (no UART)

import argparse, os, mmap, struct, sys, time, math, csv

# ---------- Q16.16 helpers ----------
SCALE_Q16 = 1 << 16

def f2q(x: float) -> int:
    x = max(min(x, 32767.9999847), -32768.0)
    return int(round(x * SCALE_Q16)) & 0xFFFFFFFF

def q2f(u32: int) -> float:
    if u32 & 0x80000000:
        u32 = -((~u32 + 1) & 0xFFFFFFFF)
    return float(u32) / SCALE_Q16

# ---------- Minimal /dev/mem MMIO ----------
class MMIO:
    def __init__(self, phys, size=0x1000):
        page = mmap.PAGESIZE
        self.fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        self.pb = phys & ~(page - 1)
        self.off = phys - self.pb
        self.mm = mmap.mmap(self.fd, size + self.off, mmap.MAP_SHARED,
                            mmap.PROT_READ | mmap.PROT_WRITE, offset=self.pb)
    def w32(self, off, v):
        self.mm[self.off+off:self.off+off+4] = struct.pack("<I", v & 0xFFFFFFFF)
    def r32(self, off):
        return struct.unpack("<I", self.mm[self.off+off:self.off+off+4])[0]
    def close(self):
        self.mm.close(); os.close(self.fd)

# AXI-GPIO register map
DATA1 = 0x00; TRI1 = 0x04
DATA2 = 0x08; TRI2 = 0x0C

class LandauHW:
    """AXI-GPIO bridge: a1 on out.DATA1, a2+TEST on out.DATA2; b on in.DATA1, status on in.DATA2[0]."""
    def __init__(self, out_base=0x41200000, in_base=0x41210000, size=0x1000):
        self.out = MMIO(out_base, size)
        self._in = MMIO(in_base,  size)
        # directions: out = outputs (0), in = inputs (1)
        self.out.w32(TRI1, 0x00000000)
        self.out.w32(TRI2, 0x00000000)
        self._in.w32(TRI1,  0xFFFFFFFF)
        self._in.w32(TRI2,  0xFFFFFFFF)

    def compute_b(self, a1_f: float, a2_f: float, test: int) -> float:
        a1_q = f2q(a1_f)
        a2_q = f2q(a2_f)
        a2_test = (a2_q & 0xFFFFFFFE) | (test & 1)  # TEST in bit0; a2 in [31:1]
        # drive
        self.out.w32(DATA1, a1_q)
        self.out.w32(DATA2, a2_test)
        # tiny settle (usually not needed, but harmless)
        # time.sleep(0.0001)
        # read
        b_raw  = self._in.r32(DATA1)
        # status = self._in.r32(DATA2) & 1  # currently always 1 in your glue
        return q2f(b_raw)

    def close(self):
        self.out.close(); self._in.close()

# ---------- Landau ODE + RK4 ----------
def landau_rhs(a1: float, a2: float, b: float):
    r2  = a1*a1 + a2*a2
    da1 = (1.0 - r2)*a1 - a2
    da2 = (1.0 - r2)*a2 + a1 + b
    return da1, da2

def rk4_step(a1: float, a2: float, b: float, dt: float):
    # Treat b as constant over this step (good for small dt)
    k1a1, k1a2 = landau_rhs(a1,             a2,             b)
    k2a1, k2a2 = landau_rhs(a1+0.5*dt*k1a1, a2+0.5*dt*k1a2, b)
    k3a1, k3a2 = landau_rhs(a1+0.5*dt*k2a1, a2+0.5*dt*k2a2, b)
    k4a1, k4a2 = landau_rhs(a1+    dt*k3a1, a2+    dt*k3a2, b)
    a1n = a1 + (dt/6.0)*(k1a1 + 2*k2a1 + 2*k3a1 + k4a1)
    a2n = a2 + (dt/6.0)*(k1a2 + 2*k2a2 + 2*k3a2 + k4a2)
    return a1n, a2n

# ---------- Main sim loop ----------
def main():
    ap = argparse.ArgumentParser(description="Landau simulation talking to FPGA via AXI-GPIO")
    ap.add_argument("--out-base", type=lambda x:int(x,0), default=0x41200000)
    ap.add_argument("--in-base",  type=lambda x:int(x,0), default=0x41210000)
    ap.add_argument("--dt",       type=float, default=0.01)
    ap.add_argument("--t-final",  type=float, default=5.0)
    ap.add_argument("--a1-0",     type=float, default=0.1)
    ap.add_argument("--a2-0",     type=float, default=0.7)
    ap.add_argument("--test",     type=int, choices=[0,1], default=0, help="1 => b = a1+1 (your glue)")
    ap.add_argument("--csv",      type=str, default="", help="optional CSV path to save results")
    ap.add_argument("--print-every", type=int, default=20, help="print every N steps")
    args = ap.parse_args()

    if os.geteuid() != 0:
        print("Run with sudo (needs /dev/mem).", file=sys.stderr); sys.exit(1)

    hw = LandauHW(args.out_base, args.in_base)
    try:
        t  = 0.0
        a1 = float(args["a1_0"]) if isinstance(args, dict) and "a1_0" in args else args.a1_0
        a2 = float(args["a2_0"]) if isinstance(args, dict) and "a2_0" in args else args.a2_0

        rows = [("t","a1","a2","b")]

        steps = int(math.ceil(args.t_final / args.dt))
        for i in range(steps+1):
            # 1) ask FPGA for b(a1,a2)
            b = hw.compute_b(a1, a2, args.test)

            if args.csv:
                rows.append((t, a1, a2, b))

            if i % max(1,args.print_every) == 0:
                print(f"t={t:7.3f}  a1={a1:+.6f}  a2={a2:+.6f}  b={b:+.6f}")

            # 2) advance state by one RK4 step using that b
            a1, a2 = rk4_step(a1, a2, b, args.dt)
            t += args.dt

        if args.csv:
            with open(args.csv, "w", newline="") as f:
                cw = csv.writer(f); cw.writerows(rows)
            print(f"Wrote {args.csv} ({len(rows)-1} rows)")

    finally:
        hw.close()

if __name__ == "__main__":
    main()
