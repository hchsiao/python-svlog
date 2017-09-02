import pydpi

class my_mod(pydpi.SvModule):
  io_spec = {
    'mod_out': pydpi.OUTPUT_REG(7),
    'mod_in': pydpi.INPUT(5),
    'reset': pydpi.INPUT(1),
    'clk': pydpi.INPUT_CLOCK(),
  }
  def mod_out(self, reset, mod_in):
    if reset == 1:
      self.state = 0
    else:
      self.state += mod_in
    return self.state