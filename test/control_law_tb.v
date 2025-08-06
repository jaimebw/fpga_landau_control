// ====================================
// File: tb_control_law.v
// Author: jaimebw
// Created: 2025-04-27
// ====================================

`timescale 1ns/1ps

module tb_control_law;

    // Inputs
    reg signed [31:0] a1;
    reg signed [31:0] a2;
    reg test;

    // Output
    wire signed [31:0] b;

    // Instantiate DUT
    LandauControlLaw dut (
        .a1(a1),
        .a2(a2),
        .test(test),
        .b(b)
    );

    // VCD Dump
    initial begin
        $dumpfile("build/sim_control_law.vcd");
        $dumpvars(0, tb_control_law);
    end

    // Test sequence
    initial begin
        // Initialize inputs
        a1 = 32'sh00020000; // 2.0 in Q16.16
        a2 = 32'sh00010000; // 1.0 in Q16.16
        test = 0;

        // Hold for some time
        #1000;

        // Change test to 1 (use test mode)
        test = 1;

        // Hold for some more time
        #1000;

        // End simulation
        $finish;
    end

endmodule
