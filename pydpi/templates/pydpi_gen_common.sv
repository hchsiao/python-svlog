import "DPI-C" context function void PyDPI_init();
import "DPI-C" context function void PyDPI_destroy();

import "DPI-C" context function void PyDPI_buf_write(byte func_id, byte addr, byte data);
import "DPI-C" context function void PyDPI_eval(byte func_id);
import "DPI-C" context function byte PyDPI_buf_read(byte func_id, byte addr);

initial begin
  PyDPI_init();
  //PyDPI_destroy();
end
