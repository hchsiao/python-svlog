parameter PYDPI_FUNC_{func_name} = 0;

function automatic [{retval_msb}:0] {func_name};
  {decl_input}
  reg [7:0] tmp;
  begin
    // big-endian fasion
    {stmnt_wbuf}
    PyDPI_eval(PYDPI_FUNC_{func_name});
    // little-endian fasion
    {stmnt_rbuf}
    // $monitor("debug: %d", {func_name});
  end
endfunction
