// ====================================
// File: UartRxPidBuffer.v
// Author: jaimebw
// Created: 2025-04-06 15:13:34
// ====================================


module UartRxPidBuffer(
    input  wire        clk,
    input  wire        rst,
    input  wire        rx_done,
    input  wire [7:0]  rx_byte,
    output reg  [31:0] a1,
    output reg  [31:0] a2,
    output reg         ready,
    output reg         test// Check if in test mode
);

    reg expect_pid;
    reg [7:0] current_pid;
    reg [7:0] a1_bytes [3:0];
    reg [7:0] a2_bytes [3:0];
    reg [7:0] received_flags;

    localparam GO_PID = 8'hFE;
    localparam TEST_PID= 8'h69;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            expect_pid <= 1;
            current_pid <= 0;
            received_flags <= 0;
            a1 <= 0;
            a2 <= 0;
            ready <= 0;
            test<= 0;
        end else begin
            ready <= 0; // default unless set below

            if (rx_done) begin
                if (expect_pid) begin
                    current_pid <= rx_byte;
                    expect_pid <= 0;
                end else begin
                    if (current_pid == GO_PID) begin
                        if (received_flags == 8'hFF) begin
                            a1 <= {a1_bytes[3], a1_bytes[2], a1_bytes[1], a1_bytes[0]};
                            a2 <= {a2_bytes[3], a2_bytes[2], a2_bytes[1], a2_bytes[0]};
                            ready <= 1;
                            received_flags <= 0; // reset for next packet
                        end
                    end else if (current_pid == TEST_PID) begin
                        if (received_flags == 8'hFF) begin
                            a1 <= {a1_bytes[3], a1_bytes[2], a1_bytes[1], a1_bytes[0]};
                            a2 <= {a2_bytes[3], a2_bytes[2], a2_bytes[1], a2_bytes[0]};
                            ready <= 1;
                            received_flags <= 0; // reset for next packet
                            test <= 1;
                        end else begin
                            ready <= 0;  // Clear ready after one cycle
                        end
                    end else begin
                        case (current_pid)
                            8'h10: begin a1_bytes[3] <= rx_byte; received_flags[0] <= 1; end  // PID = 0x10
                            8'h11: begin a1_bytes[2] <= rx_byte; received_flags[1] <= 1; end  // PID = 0x11
                            8'h12: begin a1_bytes[1] <= rx_byte; received_flags[2] <= 1; end  // PID = 0x12
                            8'h13: begin a1_bytes[0] <= rx_byte; received_flags[3] <= 1; end  // PID = 0x13
                            8'h20: begin a2_bytes[3] <= rx_byte; received_flags[4] <= 1; end  // PID = 0x20
                            8'h21: begin a2_bytes[2] <= rx_byte; received_flags[5] <= 1; end  // PID = 0x21
                            8'h22: begin a2_bytes[1] <= rx_byte; received_flags[6] <= 1; end  // PID = 0x22
                            8'h23: begin a2_bytes[0] <= rx_byte; received_flags[7] <= 1; end  // PID = 0x23
                            // TEST PID
                            8'h69: begin a2_bytes[0] <= rx_byte; a1_bytes[0]<=rx_byte; received_flags <= 8'hFF; end  // PID = 0x69


                            default: ; // Ignore unknown PIDs
                        endcase
                    end
                    expect_pid <= 1;
                end
            end
        end
    end

endmodule

