// ====================================
// File: stuart_tb.v
// Author: jaimebw
// Created: 2025-04-27 13:32:24
// ====================================

`timescale 1ns/1ps

module tb_landau_oscillator_controller;

    // Clock and reset
    reg clk;
    reg rst;

    // UART lines
    reg uart_rx;
    wire uart_tx;

    // Instantiate DUT
    landau_oscillator_controller dut (
        .clk(clk),
        .rst(rst),
        .uart_rx(uart_rx),
        .uart_tx(uart_tx)
    );

    // === Dump to VCD ===
    initial begin
        $dumpfile("build/sim.vcd"); // <- THIS is the VCD output
        $dumpvars(0, tb_landau_oscillator_controller); // <- Dump EVERYTHING under the testbench
    end

    // === Clock generation ===
    initial begin
        clk = 0;
        forever #10 clk = ~clk; // 50 MHz clock -> 20ns period
    end

    // === Reset pulse ===
    initial begin
        rst = 1;
        #100;
        rst = 0;
    end

    // === Test stimulus ===
    initial begin
        // Initialize UART RX line
        uart_rx = 1; // Idle state is high

        // Wait after reset
        #200;

        // Send fake UART frames to inject into the system
        send_uart_byte(8'h10); // PID for a1_bytes[3]
        send_uart_byte(8'h20); // PID for a2_bytes[3]
        send_uart_byte(8'h11); // PID for a1_bytes[2]
        send_uart_byte(8'h21); // PID for a2_bytes[2]
        send_uart_byte(8'h12); // PID for a1_bytes[1]
        send_uart_byte(8'h22); // PID for a2_bytes[1]
        send_uart_byte(8'h13); // PID for a1_bytes[0]
        send_uart_byte(8'h23); // PID for a2_bytes[0]
        send_uart_byte(8'h69); // TEST PID to force ready = 1

        // Wait for everything to finish
        #10000;

        // End simulation
        $finish;
    end

    // === UART transmission task ===
    task send_uart_byte(input [7:0] byte);
        integer i;
        begin
            // Start bit
            uart_rx <= 0;
            #(10416); // 9600 baud ~10416ns per bit

            // Send data bits (LSB first)
            for (i = 0; i < 8; i = i + 1) begin
                uart_rx <= byte[i];
                #(10416);
            end

            // Stop bit
            uart_rx <= 1;
            #(10416);
        end
    endtask

endmodule
