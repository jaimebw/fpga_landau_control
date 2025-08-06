# ====================================
# File: test_landau.py
# Author: jaimebw
# Created: 2025-05-10 18:16:22
# ====================================


import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, ReadOnly
from cocotb_test.simulator import run
from pathlib import Path
import sys

# Resolve this directory
sys.path.append(str(Path(__file__).resolve().parent))

TEST_PID = 0x69
CLK_FREQ = 50_000_000
BAUD_RATE = 9600
CLKS_PER_BIT = CLK_FREQ // BAUD_RATE
BIT_TIME_NS = CLKS_PER_BIT * 20  # 20ns per clock tick at 50MHzk
FRAME_BITS =8 
#TEST_FRAME = [0xAA, TEST_PID, 0xF2, 0x55]
STANDAR_CYCLE = 100_000
START_BIT = 0
STOP_BIT  = 1
START_FRAME = 0xAA
END_FRAME = 0x55
TEST_PID = 0x69


async def watch_test_flag(dut,isTest=True):
    for _ in range(STANDAR_CYCLE):
        await RisingEdge(dut.clk)
        if dut.DEBUG_test.value:
            if isTest:
                return True
    assert False, "\t[DEBUG] Test flag was never asserted"

async def watch_b(dut):
    for _ in range(STANDAR_CYCLE):
        await RisingEdge(dut.clk)
        if dut.DEBUG_ready.value ==1:
            print(f"[Monitor] B: {dut.DEBUG_b.value}")
    #b_val = dut.DEBUG_b.value

async def watch_tx(dut):
    data = []
    collecting = False
    while True:
        await RisingEdge(dut.clk)
        # Detect tx start pulse
        if dut.DEBUG_tx_start.value == 1:
            tx_byte = int(dut.DEBUG_tx_data.value)
            data.append(tx_byte)
            dut._log.info(f"[TX Watcher] Captured byte: 0x{tx_byte:02X}")

        # Optional: break condition (after known number of bytes or timeout)
        if len(data) >= 7:
            break

    return [hex(i) for i in data]


async def watch_rx_done(dut):
    for _ in range(STANDAR_CYCLE):
        await RisingEdge(dut.clk)
        if dut.DEBUG_rx_done.value != 0:
            dut._log.info("[DEBUG] RX_done detected!")
            return
    assert False, "\t[DEBUG]rx_done was never asserted"

async def watch_tx_done(dut):
    count = 0
    for _ in range(STANDAR_CYCLE):
        await RisingEdge(dut.clk)
        if dut.DEBUG_tx_done.value != 0:
            count += 1
            #print("\t[DEBUG] tx_done detected!")
    if count == 0:
        assert False, "\t[DEBUG] tx_done was never asserted"
    else:
        print(f"Tx_done change {count+1} times")




@cocotb.test()
async def top_module_normal_operation(dut):
    clock = Clock(dut.clk, 20, units="ns")  # 50 MHz
    cocotb.start_soon(clock.start())
    rx_done_task = cocotb.start_soon(watch_rx_done(dut))
    tx_changes = cocotb.start_soon(watch_tx(dut))
    tx_done = cocotb.start_soon(watch_tx_done(dut))
    b_monitor = cocotb.start_soon(watch_b(dut))

    # Reset
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    dut.rx.value = 1


    pids = [0x10,0x11,0x12,0x13,0x20,0x21,0x22,0x23]
    frames = [] 
    for pid_n,pid in enumerate(pids):
        data_bytes = [START_FRAME,pid,0xF1+pid_n, END_FRAME]
        frames.append(data_bytes)
    print("===============================================")
    print("\t\tRX FRAMES")
    for frame_n, data_bytes in enumerate(frames):
        for byte_n, data_byte in enumerate(data_bytes):
            frame_bits = [(data_byte >> i) & 1 for i in range(FRAME_BITS)]
            dut.rx.value  = 0                 
            await Timer(BIT_TIME_NS, units="ns")
            for bit_n, bit in enumerate(frame_bits):
                dut.rx.value  = bit                 # line idle
                await Timer(BIT_TIME_NS, units="ns")
            dut._log.info(f"Frame number: {frame_n}\tIteration Number: {byte_n}\tByte sent : {hex(data_byte)}")
            dut.rx.value = 1
            await Timer(BIT_TIME_NS, units="ns")
            assert dut.rx_data.value == data_byte
            assert dut.rx_busy.value == 0,  "rx_busy should be low after frame"
            await Timer(BIT_TIME_NS, units="ns")
    print("===============================================")

    #assert dut.DEBUG_test.value == 0 # THis needs to be checked somewhere
    # ===============================
    #           RX Buffer 
    # ===============================
    print("[TEST_DEBUG] Finished the sending cycle, jumpig into rx buffer...")
    #assert dut.rx_debug_done.value == 1
    # ===============================
    #           TX 
    # ===============================
    # await ReadOnly()
    # assert dut.tx_debug_data.value == 0
    # assert dut.tx_busy.value== 0
    print("[TEST_DEBUG] Finished the reading cycle, test_ended!")
    # while (dut.tx_debug_start.value !=1):
    #     await RisingEdge(dut.clk)
    await rx_done_task 
    vals = await tx_changes
    await tx_done
    await b_monitor

    print(f"Received frame {vals}")
    print(f"Value of b: {dut.DEBUG_b.value}")



def test_top_module():
    """Run simulation for top.v"""
    this_dir = Path(__file__).resolve().parent
    rtl_dir  = this_dir.parent / "src"
    jaime_dir = this_dir.parent.parent / "jaime_modules"/"src"
    mod_name = Path(__file__).stem

    assert jaime_dir.exists(), f" Cant find Jaime dir: {jaime_dir}"
    assert rtl_dir.exists(), f" Cant find current dir: {rtl_dir}"

    run(
        toplevel="LandauOscillatorController",
        module=mod_name,                    
        verilog_sources=[
            rtl_dir / "landau_oscillator_controller.v",
            jaime_dir/ "uart_rx.v",
            jaime_dir/ "uart_tx.v",
            jaime_dir/ "uart_tx_pid_buffer.v",
            jaime_dir/ "uart_rx_pid_buffer.v",
            jaime_dir/ "control_law.v",
        ],
        # parameters={
        #     "K1": "32'sd65536",             # example parameter override
        #     "K2": "32'sd65536",
        # },
        defines = ["SIM_MODE"],
        timescale="1ns/1ns",
        waves=True,
        sim_build=this_dir / f"sim_{mod_name}",
    )

