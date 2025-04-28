# ====================================
# File: sim.py
# Author: jaimebw
# Created: 2025-04-26 19:01:06
# ====================================
import argparse
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



