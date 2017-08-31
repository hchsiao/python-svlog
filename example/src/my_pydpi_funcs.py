import pydpi

pydpi.export('nxt_out', retval_width=1, params_width=(1, 1))
def nxt_out(out, reset):
  print out, reset
  if reset:
    return 0
  elif out:
    return 0
  else:
    return 1
