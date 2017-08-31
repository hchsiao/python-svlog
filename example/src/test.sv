`include "mod_mem.sv"

module test;
  parameter CLK_PERIOD = 10;
  parameter SIM_CYCLE = 6;

	reg reset;
	reg clk;
  always #(CLK_PERIOD/2) begin
    clk = ~clk;
  end

	initial begin
    $monitor("out=%d", out);
    clk = 0;
    reset = 1;
    #(CLK_PERIOD*1) reset = 0;
    #(SIM_CYCLE*CLK_PERIOD) $finish;

	end

  mod_mem #(
  )IM(
    .out(out),
    .clk(clk),
    .reset(reset)
  );

endmodule

