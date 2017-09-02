import struct 
import string
import inspect
import importlib

mods = {}

PORT_OUTPUT = 1
def OUTPUT(width):
  return PORT_OUTPUT, width
PORT_OUTPUT_REG = 2
def OUTPUT_REG(width):
  return PORT_OUTPUT_REG, width
PORT_INPUT = 3
def INPUT(width):
  return PORT_INPUT, width
PORT_INPUT_CLOCK = 4
def INPUT_CLOCK():
  return PORT_INPUT_CLOCK, 1

class Wires:
  def __init__(self, width):
    self.width = width

class SvModule:
  def __init__(self):
    print('SvModule created')

class SvFunctionHandle:
  func_name_list = []
  func_map = {}

  @staticmethod
  def get_func_hndl_by_id(idx):
    f_name = SvFunctionHandle.func_name_list[idx]
    return SvFunctionHandle.func_map[f_name]

  @staticmethod
  def get_func_hndl_by_name(f_name):
    return SvFunctionHandle.func_map[f_name]

  def __init__(self, name, mod_name, retval_width=None, params_width=None):
    self.retval_width = retval_width
    self.params_width = params_width
    self.mod_name = mod_name
    self.func_name = name
    param_width_total = sum(params_width)
    param_required_byte = (param_width_total+7)/8
    retval_required_byte = (retval_width+7)/8
    self.buf = ['\0'] * max(param_required_byte, retval_required_byte)
    SvFunctionHandle.func_name_list.append(name)
    SvFunctionHandle.func_map[name] = self

  def __call__(self):
    # unpack each arg
    argv = []
    for in_idx in range(len(self.params_width)):
      loaded_width = sum(self.params_width[:in_idx])
      to_load_width = self.params_width[in_idx]
      buf_idx_msb = loaded_width / 8
      buf_idx_lsb = (loaded_width + to_load_width - 1) / 8
      data_packs = string.join(self.buf[buf_idx_msb:buf_idx_lsb+1], '')
      data_uint_8 = list(struct.unpack('B'*len(data_packs), data_packs))
      msb = 7 - (loaded_width % 8)
      lsb = 7 - ((loaded_width + to_load_width - 1) % 8)
      data_uint_8[0] &= 2**(msb+1) - 1
      data_uint_8[-1] &= ~(2**(lsb) - 1)
      data_masked_pack = struct.pack('B'*len(data_packs), *data_uint_8)
      padding_len = 8 - len(data_masked_pack)
      data_masked_pack = '\0'*padding_len + data_masked_pack
      data = struct.unpack('>Q', data_masked_pack)[0] >> lsb
      argv.append(data)
    # call the function
    callback = getattr(mods[self.mod_name], self.func_name)
    retval = callback(*argv)
    # pack return value (retval)
    retval_required_byte = (self.retval_width+7)/8
    retval_mask = 2**self.retval_width - 1
    retval_pack = struct.pack('<Q', retval & retval_mask)
    self.buf[:retval_required_byte] = retval_pack[:retval_required_byte]

def get_func_hndl(idx):
  return SvFunctionHandle.get_func_hndl_by_id(idx)

def export(name, retval_width=None, params_width=None):
  callback = None
  stk = inspect.stack()[1]
  mod = inspect.getmodule(stk[0])
  mod_name = mod.__name__
  hndl = SvFunctionHandle(name, mod_name, retval_width, params_width)

def __reg_mod(mod):
  mods[mod.__name__] = mod

def get_params():
  import anyconfig
  config_file = 'svlog-cfg.json' # TODO: use multi config files
  conf = anyconfig.load(config_file, 'json')
  return conf['params']

