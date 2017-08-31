import pydpi

# (Offline) import each module and scan for classes w/ io_spec static member
# (Online) maintain one instance
class my_mod(pydpi.VModule):
  io_spec = {
    'foo': pydpi.OUTPUT_REG(4),
    'bar': pydpi.OUTPUT(1),
    'baz': pydpi.INPUT(4),
    'reset': pydpi.INPUT(1),
    'clk': pydpi.INPUT_CLOCK(),
  }
  def bar(self, baz, reset):
    return ~baz
  def foo(self, baz, reset):
    return 0 if reset else -baz
