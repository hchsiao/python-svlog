`include "pydpi_gen_mod_my_mod.sv"

module test;
  parameter CLK_PERIOD = 10;
  parameter SIM_CYCLE = 6;

	reg reset;
	reg clk;
  always #(CLK_PERIOD/2) begin
    clk = ~clk;
  end

  wire [6:0] mod_out;
  wire [4:0] mod_in = 3;
	initial begin
    $monitor("mod_out=%d", mod_out);
    clk = 0;
    reset = 1;
    #(CLK_PERIOD*1) reset = 0;
    #(SIM_CYCLE*CLK_PERIOD) $finish;

	end

  my_mod #(
  )MOD1(
    .mod_out(mod_out),
    .mod_in(mod_in),
    .clk(clk),
    .reset(reset)
  );

endmodule

