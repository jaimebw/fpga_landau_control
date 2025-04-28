// ====================================
// File: control_law.v
// Author: jaimebw
// Created: 2025-04-06 13:54:08
// ====================================

module LandauControlLaw#(
    parameter signed [31:0] K1 = -32'sd13107, // -0.2 in Q16.16
    parameter signed [31:0] K2 = -32'sd26214  // -0.4 in Q16.16
)(
    input wire signed [31:0] a1,
    input wire signed [31:0] a2,
    input wire test,
    output reg signed [31:0] b
);

    reg signed [63:0] mult1;
    reg signed [63:0] mult2;
    reg signed [63:0] sum;

    always @(*) begin
        if (test) begin
            mult1 = 0;
            mult2 = 0;
            sum = {32'b0, a1 + 32'sh00010000}; // Add 1.0
            b = a1 + 32'sh00010000;            // Output is a1 + 1.0
        end else begin
            mult1 = a1 * K1;
            mult2 = a2 * K2;
            sum = mult1 + mult2;
            b = sum[47:16]; // Take Q16.16 result
        end
    end

endmodule

