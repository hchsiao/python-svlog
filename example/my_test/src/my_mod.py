import pydpi

class my_mod(pydpi.SvModule):
  io_spec = {
    'out': pydpi.OUTPUT_REG(4),
    'reset': pydpi.INPUT(1),
    'clk': pydpi.INPUT_CLOCK(),
  }
  def out(self, reset):
    return 0 if reset else 1
