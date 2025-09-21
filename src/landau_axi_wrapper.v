module landau_axi (
    // AXI4-Lite interface (bundled)
    (* X_INTERFACE_PARAMETER = "DATA_WIDTH 32, ADDR_WIDTH 4, PROTOCOL AXI4LITE" *)
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI" *)
    input  wire [3:0]   s_axi_awaddr,
    input  wire         s_axi_awvalid,
    output wire         s_axi_awready,
    input  wire [31:0]  s_axi_wdata,
    input  wire [3:0]   s_axi_wstrb,
    input  wire         s_axi_wvalid,
    output wire         s_axi_wready,
    output wire [1:0]   s_axi_bresp,
    output wire         s_axi_bvalid,
    input  wire         s_axi_bready,
    input  wire [3:0]   s_axi_araddr,
    input  wire         s_axi_arvalid,
    output wire         s_axi_arready,
    output wire [31:0]  s_axi_rdata,
    output wire [1:0]   s_axi_rresp,
    output wire         s_axi_rvalid,
    input  wire         s_axi_rready,

    // Clock and Reset
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 CLK CLK" *)
    input  wire clk,

    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 RST RST" *)
    input  wire rst
);

    // Internal registers
    wire [31:0] a1;
    wire [31:0] a2;
    wire [31:0] b;

    // Connect your control law module
    LandauControlLaw ctrl (
        .a1(a1),
        .a2(a2),
        .test(1'b1),
        .b(b)
    );

    // AXI register interface
    axi_regs axi_if (
        .clk(clk),
        .rst(rst),
        .awaddr(s_axi_awaddr),
        .awvalid(s_axi_awvalid),
        .awready(s_axi_awready),
        .wdata(s_axi_wdata),
        .wstrb(s_axi_wstrb),
        .wvalid(s_axi_wvalid),
        .wready(s_axi_wready),
        .bresp(s_axi_bresp),
        .bvalid(s_axi_bvalid),
        .bready(s_axi_bready),
        .araddr(s_axi_araddr),
        .arvalid(s_axi_arvalid),
        .arready(s_axi_arready),
        .rdata(s_axi_rdata),
        .rresp(s_axi_rresp),
        .rvalid(s_axi_rvalid),
        .rready(s_axi_rready),
        .a1_out(a1),
        .a2_out(a2),
        .b_in(b)
    );

endmodule
