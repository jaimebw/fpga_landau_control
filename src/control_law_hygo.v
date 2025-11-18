module LandauControlLaw #(
    // Q16.16 constants
    parameter signed [31:0] C      = 32'sd475915,   // 7.262196 * 2^16
    parameter signed [31:0] COEFF3 = -32'sd10923,   // -1/6    * 2^16
    parameter signed [31:0] COEFF5 =  32'sd546      //  1/120  * 2^16
)(
    input  wire signed [31:0] a1,  // Q16.16
    input  wire signed [31:0] a2,  // Q16.16
    input  wire               test,
    output reg  signed [31:0] b    // Q16.16
);

    // Fixed-point multiply: Q16.16 * Q16.16 -> Q16.16
    function automatic signed [31:0] qmul;
        input signed [31:0] x;
        input signed [31:0] y;
        reg   signed [63:0] tmp;
    begin
        tmp  = x * y;          // Q32.32
        qmul = tmp[47:16];     // back to Q16.16
    end
    endfunction

    // Powers of a1 in Q16.16
    wire signed [31:0] a1_sq  = qmul(a1, a1);       // a1^2
    wire signed [31:0] a1_cu  = qmul(a1_sq, a1);    // a1^3
    wire signed [31:0] a1_4   = qmul(a1_cu, a1);    // a1^4
    wire signed [31:0] a1_p5  = qmul(a1_4, a1);     // a1^5

    // Nonlinear terms: -a1^3/6 + a1^5/120 (both Q16.16)
    wire signed [31:0] term3  = qmul(a1_cu, COEFF3);
    wire signed [31:0] term5  = qmul(a1_p5, COEFF5);

    // 2*a1 in Q16.16
    wire signed [31:0] term2a1 = a1 <<< 1;

    // poly = 2a1 - a1^3/6 + a1^5/120 - a2  (Q16.16)
    wire signed [31:0] poly = term2a1 + term3 + term5 - a2;

    // b = C * poly  (Q16.16)
    wire signed [31:0] control_result = qmul(C, poly);

    always @(*) begin
        if (test) begin
            b = a1 + 32'sh00020000; // test: a1 + 1.0
        end else begin
            b = control_result;
        end
    end

endmodule
