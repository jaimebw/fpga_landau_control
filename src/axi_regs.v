module AxiRegs (
    input  wire         clk,
    input  wire         rst,
    input  wire [3:0]   awaddr,
    input  wire         awvalid,
    output reg          awready,
    input  wire [31:0]  wdata,
    input  wire [3:0]   wstrb,
    input  wire         wvalid,
    output reg          wready,
    output wire [1:0]   bresp,
    output reg          bvalid,
    input  wire         bready,
    input  wire [3:0]   araddr,
    input  wire         arvalid,
    output reg          arready,
    output reg [31:0]   rdata,
    output wire [1:0]   rresp,
    output reg          rvalid,
    input  wire         rready,

    output reg [31:0]   a1_out,
    output reg [31:0]   a2_out,
    input  wire [31:0]  b_in
);
    reg [31:0] regfile [0:2];

    // Write FSM
    always @(posedge clk) begin
        if (rst) begin
            awready <= 0; wready <= 0; bvalid <= 0;
        end else begin
            awready <= ~awready & awvalid;
            wready  <= ~wready & wvalid;
            bvalid  <= awvalid & wvalid;
            if (awvalid & wvalid) begin
                case (awaddr[3:2])
                    2'd0: regfile[0] <= wdata;
                    2'd1: regfile[1] <= wdata;
                    default: ;
                endcase
            end
        end
        a1_out <= regfile[0];
        a2_out <= regfile[1];
    end

    // Read FSM
    always @(posedge clk) begin
        if (rst) begin
            arready <= 0; rvalid <= 0;
        end else begin
            arready <= ~arready & arvalid;
            rvalid  <= arvalid;
            case (araddr[3:2])
                2'd0: rdata <= regfile[0];
                2'd1: rdata <= regfile[1];
                2'd2: rdata <= b_in;
                default: rdata <= 32'hDEAD_BEEF;
            endcase
        end
    end

    assign bresp = 2'b00;
    assign rresp = 2'b00;

endmodule
