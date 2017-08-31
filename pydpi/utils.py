import string
import os

input_path = './src/'
prefix = 'cache/'
this_dir, this_filename = os.path.split(__file__)
tmpl_dir = os.path.join(this_dir, "templates/")
print('prefix: {}'.format(prefix))

FILE_SIZE_LMT = 1000000 # 1 MiB
PYDPI_FILE_FEAT_STR = 'pydpi.export('
PYDPI_PARAM_NAME_RETVAL = 'retval_width'
PYDPI_PARAM_NAME_PARAM = 'params_width'
PYDPI_SYS_WORD_IN = 'input [{msb}:0] pydpi_arg{idx};'
PYDPI_SYS_WBUF = 'PyDPI_buf_write(PYDPI_FUNC_{func_name}, {buf_addr}, {{{data}}});'
PYDPI_SYS_RBUF = 'tmp = PyDPI_buf_read(PYDPI_FUNC_{func_name}, {buf_addr});'
PYDPI_SYS_FLUSH = '{func_name}[{retval_msb}:{retval_lsb}] = tmp[{msb}:{lsb}];'
def is_candidate_file(fname):
  fpath = input_path + fname
  if not os.path.isfile(fpath):
    return False
  elif fname[0] == '.':
    return False
  elif fname[-3:] != '.py':
    return False
  elif os.path.getsize(fpath) > FILE_SIZE_LMT:
    return False
  elif not PYDPI_FILE_FEAT_STR in open(fpath).read():
    return False
  else:
    return True

def gen(tmpl_fname, params):
  tmpl_file = open(tmpl_dir + tmpl_fname)
  tmpl = tmpl_file.read()

  fname = tmpl_fname.format(**params)
  f = open(prefix + fname, 'w')
  f.write(tmpl.format(**params))
  f.close()

def run_gen():
  gen('pydpi_gen_common.sv', {})

  f = open(prefix + 'pydpi_gen_registration.py', 'w')
  func_file_list = [fn[:-3] for fn in os.listdir(input_path) if is_candidate_file(fn)]
  f.write(string.join(['import ' + fn for fn in func_file_list], '\n'))
  f.write('\nimport pydpi\n')
  f.write(string.join(['pydpi.__reg_mod(' + fn + ')' for fn in func_file_list], '\n'))
  f.close()

  func_specs = {}
  for fn in func_file_list:
    src = open(input_path + fn + '.py').read().split('\n')
    export_statements = [line for line in src if PYDPI_FILE_FEAT_STR in line]
    for stmnt in export_statements:
      stmnt = stmnt.replace(PYDPI_FILE_FEAT_STR, '').replace('\'', '')[:-1]
      stmnt = stmnt.replace(PYDPI_PARAM_NAME_RETVAL, '\n'+PYDPI_PARAM_NAME_RETVAL)
      stmnt = stmnt.replace(PYDPI_PARAM_NAME_PARAM, '\n'+PYDPI_PARAM_NAME_PARAM)
      func_name = stmnt.split('\n')[0].strip().replace(',','')
      for i in range(1, 3):
        arg = stmnt.split('\n')[i]
        argn = arg.split('=')[0]
        argv = arg.split('=')[1].strip()[:-1].replace('(', '').replace(')', '').replace(' ', '')
        if argn == PYDPI_PARAM_NAME_RETVAL:
          retval_width = int(argv)
        elif argn == PYDPI_PARAM_NAME_PARAM:
          params_width = [int(val) for val in argv.split(',')]
      func_specs[func_name] = (retval_width, params_width)

  for func_name in func_specs.keys():
    func_spec = func_specs[func_name]
    out_width = func_spec[0]
    in_widths = func_spec[1]
    in_width = sum(in_widths)
    decl_input = ''
    stmnt_wbuf = ''
    stmnt_rbuf = ''
    for idx in range(len(in_widths)):
      in_w = in_widths[idx]
      decl_input += PYDPI_SYS_WORD_IN.format(**{
        'idx': idx,
        'msb': in_w - 1,
        }) + '\n  '
    for idx in range((in_width+7)/8):
      data = ''
      loaded_width = 8*idx
      for in_idx in range(len(in_widths)):
        loaded_width -= in_widths[in_idx]
        if loaded_width < 0:
          break
      unallocated_width = 8
      while unallocated_width > 0:
        if in_idx >= len(in_widths):
          data += '{}\'b0, '.format(unallocated_width)
          break
        in_w = in_widths[in_idx]
        msb = -1 - loaded_width
        loaded_width = 0
        msb = in_w - 1 if msb < 0 else msb
        lsb = 0 if msb - unallocated_width + 1 < 0 else msb - unallocated_width + 1
        data += 'pydpi_arg{idx}[{msb}:{lsb}], '.format(**{
          'idx': in_idx,
          'msb': msb,
          'lsb': lsb,
          })
        in_idx += 1
        unallocated_width -= msb - lsb + 1
      stmnt_wbuf += PYDPI_SYS_WBUF.format(**{
        'func_name': func_name,
        'buf_addr': idx,
        'data': data[:-2]
        }) + '\n    '
    for idx in range((out_width+7)/8):
      if idx == (out_width+7)/8-1:
        read_width = 8 if out_width % 8 == 0 else out_width % 8
      else:
        read_width = 8
      stmnt_rbuf += PYDPI_SYS_RBUF.format(**{
        'func_name': func_name,
        'buf_addr': idx,
        }) + '\n    '
      stmnt_rbuf += PYDPI_SYS_FLUSH.format(**{
        'func_name': func_name,
        'retval_msb': idx*8 + read_width - 1,
        'retval_lsb': idx*8,
        'msb': read_width - 1,
        'lsb': 0,
        }) + '\n    '
    gen('pydpi_gen_func_{func_name}.sv', {
      'func_name': func_name,
      'retval_msb': out_width-1,
      'decl_input': decl_input.strip(),
      'stmnt_wbuf': stmnt_wbuf.strip(),
      'stmnt_rbuf': stmnt_rbuf.strip(),
      })
