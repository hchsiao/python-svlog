import struct
import os, sys, traceback

import pydpi
try:
  import pydpi_gen_registration
except ImportError:
  print('pydpi_gen_registration module not found')

__last_callback_cmd = 0

def _Set(func_id, addr, data):
  f = pydpi.get_func_hndl(func_id)
  f.buf[addr] = struct.pack('B', data)

def _Get(func_id, addr):
  f = pydpi.get_func_hndl(func_id)
  return struct.unpack('B', f.buf[addr])[0]

def _Eval(func_id):
  global __last_callback_cmd
  try:
    f = pydpi.get_func_hndl(func_id)
    f()
    retval = __last_callback_cmd
    __last_callback_cmd = 0
    return retval
  except Exception, e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print 'ERROR!!!', e
    print(exc_type, fname, exc_tb.tb_lineno)
    traceback.print_exc()
    raise

def _Destroy():
  return

def finish():
  global __last_callback_cmd
  __last_callback_cmd = 1
