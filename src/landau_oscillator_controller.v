// ====================================
// File: landau_oscillator_controller.v
// Author: jaimebw
// Created: 2025-04-06 14:20:35
// ====================================

module landau_oscillator_controller(
    input wire clk,
    input wire rst,
    input wire uart_rx,
    output wire uart_tx
);

    // UART RX interface
    wire [7:0] rx_data;
    wire       rx_done;
    wire       rx_busy;

    // PID buffer output
    wire [31:0] a1;
    wire [31:0] a2;
    wire        ready;
    wire        test; // FIX: wire, not reg!

    // Control output
    wire [31:0] b;

    // UART TX interface
    wire [7:0] tx_data;
    wire       tx_done;
    wire       tx_start; // FIX: wire, not reg!

    // Frame for UART transmission
    wire [9:0] frame_data = {1'b1, tx_data, 1'b0}; // stop bit, 8 data bits, start bit

    // === UART Receiver ===
    UartRx #(
        .CLK_FREQ(50_000_000),
        .BAUD_RATE(9600),
        .FRAME_BITS(8)
    ) uart_rx_inst (
        .clk(clk),
        .rst(rst),
        .rx(uart_rx),
        .rx_data(rx_data),
        .rx_done(rx_done),
        .rx_busy(rx_busy)
    );

    // === PID-aware UART Buffer ===
    UartRxPidBuffer rx_pid_buffer (
        .clk(clk),
        .rst(rst),
        .rx_done(rx_done),
        .rx_byte(rx_data),
        .a1(a1),
        .a2(a2),
        .ready(ready),
        .test(test)
    );

    // === Control Law ===
    LandauControlLaw ctrl_law(
        .a1(a1),
        .a2(a2),
        .test(test),
        .b(b)
    );

    // === UART TX Buffer ===
    UartTxPidBuffer uart_tx_pid_buffer (
        .clk(clk),
        .rst(rst),
        .tx_float(b),
        .tx_valid(ready), // usually valid when ready
        .tx_busy(tx_busy),
        .test(test),
        .tx_data(tx_data),
        .tx_start(tx_start)
    );

    // === UART Transmitter ===
    UartTx uart_tx_inst (
        .clk(clk),
        .rst(rst),
        .frame_data(frame_data),
        .tx_start(tx_start),
        .tx_busy(tx_busy),
        .tx(uart_tx),
        .tx_done(tx_done)
    );

endmodule

