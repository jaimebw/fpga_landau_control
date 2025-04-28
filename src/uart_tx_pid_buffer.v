// ====================================
// File: uart_tx_pid_buffer.v
// Author: jaimebw
// Created: 2025-04-26 19:59:30
// ====================================

module UartTxPidBuffer(
    input wire clk,
    input wire rst,
    input wire [31:0] tx_float,      // Float to be sent over UART
    input wire tx_valid,             // Pulse to trigger transmission
    input wire tx_busy,              // UART transmitter busy flag
    input wire test,                 // Flag to indicate if this is a test transmission
    output reg [7:0] tx_data,        // Byte to send via uart_tx
    output reg tx_start              // Pulse to trigger uart_tx
    
);

    reg [2:0] byte_index;            // Now need 3 bits to count 0-6 (START + PID + 4 data bytes + END)
    reg sending;
    reg [31:0] buffer;

    localparam TEST_PID = 8'h42;     // PID for test frames
    localparam DATA_PID = 8'h69;     // PID for normal data frames
    localparam START_DELIMITER = 8'hAA; // Start of frame delimiter
    localparam END_DELIMITER = 8'h55;   // End of frame delimiter

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            tx_data <= 8'b0;
            tx_start <= 0;
            byte_index <= 0;
            sending <= 0;
            buffer <= 0;
        end else begin
            tx_start <= 0; // default

            if (tx_valid && !sending) begin
                buffer <= tx_float;
                byte_index <= 0;
                sending <= 1;
            end

            if (sending && !tx_busy) begin
                case (byte_index)
                    3'd0: tx_data <= START_DELIMITER;             // Start delimiter
                    3'd1: tx_data <= test ? TEST_PID : DATA_PID;  // PID byte
                    3'd2: tx_data <= buffer[7:0];                 // Data bytes
                    3'd3: tx_data <= buffer[15:8];
                    3'd4: tx_data <= buffer[23:16];
                    3'd5: tx_data <= buffer[31:24];
                    3'd6: tx_data <= END_DELIMITER;               // End delimiter
                endcase

                tx_start <= 1;
                byte_index <= byte_index + 1;

                if (byte_index == 3'd6)  // Now we send 7 bytes total (START + PID + 4 data bytes + END)
                    sending <= 0;
            end
        end
    end

endmodule

