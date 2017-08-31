module mod_mem #(
  parameter IM_SIZE = 4096,
  parameter LOG_IM_SIZE = 12

)
(
  output reg out,
  input wire clk,
  input wire reset

);

  `include "pydpi_gen_common.sv"
  `include "pydpi_gen_func_nxt_out.sv"

  always@(posedge clk) begin
    out <= nxt_out(out, reset);

  end

endmodule

