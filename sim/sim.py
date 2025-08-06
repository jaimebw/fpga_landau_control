# ====================================
# File: sim.py
# Author: jaimebw
# Created: 2025-04-26 19:01:06
# ====================================
import argparse
import numpy as np
import serial
import random
from enum import Enum



DEBUG = True
# UART PARAMS
INIT_FRAME = 0xAA
END_FRAME = 0x55

class PIDS(Enum):
    A1_0 = 0x10
    A1_1 = 0x11
    A1_2 = 0x12
    A1_3 = 0x13

    A2_0 = 0x20
    A2_1 = 0x21
    A2_2 = 0x22
    A2_3 = 0x23

    TEST_PID_TX = 0x69
    TEST_PID_RX = 0x42
    START_PID = 0xFE



def float_to_q16_bytes(x: float) -> tuple[int, int, int, int]:
    """
    float  -> 4-byte big-endian signed Q16.16
    Returns a tuple (b3, b2, b1, b0) each 0-255.
    """
    # saturate to representable range
    x = max(min(x, 32767.9999847), -32768.0)
    raw = int(round(x * SCALE_Q16)) & 0xFFFFFFFF   # 32-bit two’s-complement
    return (
        (raw >> 24) & 0xFF,   # MSB
        (raw >> 16) & 0xFF,
        (raw >>  8) & 0xFF,
        (raw      ) & 0xFF,   # LSB
    )

def q16_int_to_float(raw: int) -> float:
    if raw & 0x80000000:
        raw = -((~raw + 1) & 0xFFFFFFFF)
    return raw / (1 << 16)

def landau(t, y, b):
    a1, a2 = y
    r2 = a1*a1 + a2*a2
    da1 = (1.0 - r2) * a1 - a2          
    da2 = (1.0 - r2) * a2 + a1 + b      
    return [da1, da2]

def sim_b(a1:float,a2:float) ->float:
    """
    Simulating B in case no FPGA is added to loop

    Two options:
        return a1*b1 + a2*b2
    Return the complex shit of below
       return  4.88419 * (np.sin(a1)+a1-a2)/0.67255
    """
    # b1 = 0.3
    # b2 = 0.2
    
    # return a1*b1 + a2*b2
    return 4.88419 * (np.sin(a1)+a1-a2)/0.67255

def sim_loop_t(dt=0.01, t_final=10.0, a1_0=0.1, a2_0=0.7):
    """
    Sim thread. This calculates the value of the sim
    """
    solver = ode(landau).set_integrator("dopri5")
    b      = 0.0                              # first step uses b=0
    solver.set_initial_value([a1_0, a2_0], 0.0)
    solver.set_f_params(b)

    while solver.successful() and solver.t < t_final and not stop_flag.is_set():
        solver.integrate(solver.t + dt)
        a1, a2 = solver.y
        t_now  = solver.t

        if SIMULATED:
            b = sim_b(a1,a2)
            solver.set_f_params(b)

        else:
            try:
                q_sim2fpga.put_nowait((t_now, a1, a2))
            except Full:
                q_sim2fpga.get_nowait()           # drop stale item
                q_sim2fpga.put_nowait((t_now, a1, a2))

            try:
                b = q_fpga2sim.get(timeout=1.0)   # 1-s timeout for robustness
            except Empty:
                print("[SIM] No control input -- keeping old b")
        solver.set_f_params(b)
        
        capture_evolution(t_now,b,a1,a2)
    stop_flag.set()   # tell IO thread to shut down when done

def packet_serializer_out(a1:float,a2:float)->List[bytes]:
    vals_a1 = float_to_q16_bytes(a1)
    vals_a2 = float_to_q16_bytes(a2)
    uart_packets = []

    for index,val in enumerate(vals_a1):
        uart_packets.append(PIDS.START_FRAME.value)
        uart_packets.append(PIDS.A1_0.value+index)
        uart_packets.append(val)
        uart_packets.append(PIDS.END_FRAME.value)

    for index,val in enumerate(vals_a2):
        uart_packets.append(PIDS.START_FRAME.value)
        uart_packets.append(PIDS.A2_0.value+index)
        uart_packets.append(val)
        uart_packets.append(PIDS.END_FRAME.value)

    return uart_packets

def packet_deserializer(ser: serial.Serial) -> float:
    while True:
        byte = ser.read(1)
        if not byte:
            return 0  # timeout or serial failure
        
        if byte[0] == PIDS.START_FRAME.value:
            pid = ser.read(1)
            if not pid or pid[0] != PIDS.TEST_PID_TX.value:
                continue  # wrong PID, restart
            
            payload = ser.read(4)
            if len(payload) != 4:
                return 0  # incomplete payload
            
            raw_val, = struct.unpack(">i", payload)
            return q16_int_to_float(raw_val)

def io_loop_t(port="/dev/ttyUSB0", baud=9600):
    """
    IO thread. This communicates with the FPGA.
    """
    try:
        ser = serial.Serial(port, baud, timeout=0.1)
        print("[IO]  Serial link open:", ser.portstr)
    except serial.SerialException as e:
        print("[IO]  Serial error:", e)
        stop_flag.set()
        return

    while not stop_flag.is_set():
        # 1) wait for the newest a1,a2 from SIM
        try:
            t_now, a1, a2 = q_sim2fpga.get(timeout=0.1)
            packets = packet_serializer_out(a1,a2)
        except Empty:
            continue
        for packet in packets:
            ser.write(packet)
        try:
            b = packet_deserializer(ser)
            try:
                q_fpga2sim.put_nowait(b)
            except Full:
                q_fpga2sim.get_nowait()
                q_fpga2sim.put_nowait(b)
        except ValueError:
            print("FPGA ERROR")

    ser.close()
    print("[IO]  Serial closed - exiting")
>>>>>>> Stashed changes

def test_uart(port:str,baudrate:str,timeout:float)->None:
    """
    Simple function to test the connection to the FPGA through a serial interface
    using UART.

    The FPGA has a PID that if detected, it will echo the value that is being sent +1.
    For example, if I send 0x1, the FPGA will responde 0x02
    """
    try:
        # Open serial connection
        ser = serial.Serial(port=port, baudrate=int(baudrate), timeout=timeout)
        print(f"Connected to {port} at {baudrate} baud")
        
        # Send test message
        for _ in range(5):
            val = random.randint(0,255)
            ser.write(bytes([INIT_FRAME, PIDS.TEST_PID_TX.value, val, END_FRAME]))
            print(f"Sent: {hex(INIT_FRAME)} {hex(PIDS.TEST_PID_TX.value)} {hex(val)} {hex(END_FRAME)}")
            
            # Read response
            response = ser.read(4)  # Read 4 bytes: INIT_FRAME, PID, val+1, END_FRAME
            if len(response) == 4:
                print(f"Received: {hex(response[0])} {hex(response[1])} {hex(response[2])} {hex(response[3])}")
                if response[0] == INIT_FRAME and response[1] == PIDS.TEST_PID_RX.value and response[2] == (val + 1) % 256 and response[3] == END_FRAME:
                    print(f"Response valid: PID=0x42, value={hex(response[2])} (original+1)")
                else:
                    print(f"Invalid response format ❌")
            else:
                print(f"Incomplete response: {response.hex()} ⚠️")
            
        
        # Close the connection
        ser.close()
        print("Test passed! ✅\nConnection closed 🔌")
        
    except serial.SerialException as e:
        print(f"Error: Could not open port {port}: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UART communication with FPGA")
    parser.add_argument("-p", "--port", type=str, required=True, help="Serial port to connect to")
    parser.add_argument("-b", "--baudrate", type=int, default=9600, help="Baud rate (default: 9600)")
    parser.add_argument("-t", "--timeout", type=float, default=1.0, help="Serial timeout in seconds (default: 1.0)")
    parser.add_argument("-m", "--mode", type=str, default="test", help="Mode of operation: test or normal")
    args = parser.parse_args()

    if args.mode == "test":
        test_uart(args.port,args.baudrate,args.timeout)



