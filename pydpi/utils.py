import string
import os.path
import subprocess
import shutil
import anyconfig

this_dir, this_filename = os.path.split(__file__)
tmpl_dir = os.path.join(this_dir, "templates/")
home_dir = os.path.expanduser('~')
config_file = os.path.join(home_dir, '.python-svlog-cfg')
if not os.path.isfile(config_file):
  anyconfig.dump({
    'input_path': './src/',
    'prefix': 'cache/',
    'dpi_inc': '/opt/Cadence/INCISIV/cur/tools/include',
    'py_cfg': 'python-config',
    }, config_file, 'yaml')
  print('Created {} since it does not exist. Please fill the fields and re-run'.format(config_file))
  exit(1)
else:
  conf = anyconfig.load(config_file, 'yaml')
  input_path = conf['input_path']

CC = 'gcc'
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

def call(arg_list, env=None):
  if not env is None:
    process = subprocess.Popen(arg_list, env=env, stdout=subprocess.PIPE)
  else:
    process = subprocess.Popen(arg_list, stdout=subprocess.PIPE)
  while True:
    line = process.stdout.readline()
    if line != b'':
      os.write(1, line)
    else:
      break
  stdoutdata, stderrdata = process.communicate()
  return process.returncode

def copytree(src, dst, symlinks=False, ignore=None):
  for item in os.listdir(src):
    s = os.path.join(src, item)
    d = os.path.join(dst, item)
    if os.path.isdir(s):
      shutil.copytree(s, d, symlinks, ignore)
    else:
      shutil.copy2(s, d)

def gen(tmpl_fname, params):
  tmpl_file = open(tmpl_dir + tmpl_fname)
  tmpl = tmpl_file.read()

  fname = tmpl_fname.format(**params)
  f = open(conf['prefix'] + fname, 'w')
  f.write(tmpl.format(**params))
  f.close()

def run_gen():
  if not os.path.exists(conf['prefix']):
    os.mkdir(conf['prefix'])

  gen('pydpi_gen_common.sv', {})

  f = open(conf['prefix'] + 'pydpi_gen_registration.py', 'w')
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

def run_build_bridge():
  kwargs = {
      'in_file': os.path.join(this_dir, 'src/bridge/ies/invoke.c'),
      'out_file': os.path.join(conf['prefix'], 'invoke.so'),
      'inc': conf['dpi_inc'],
      'cflags': subprocess.check_output([conf['py_cfg'], '--cflags']),
      'ldflags': subprocess.check_output([conf['py_cfg'], '--ldflags']),
      }
  flags = '-fPIC -shared -o {out_file} {in_file} -I{inc} {cflags} {ldflags}'.format(**kwargs)
  assert 0 == call([CC] + flags.split())
  print('Build success')

def run_run():
  kwargs = {
      }
  flags = '+nc64bit +sv +sv_lib=./cache/invoke.so +access+r +incdir+"./cache" -mccodegen cache/test.sv'.format(**kwargs)
  my_env = os.environ.copy()
  my_env["PYTHONPATH"] = "./cache:" + my_env["PYTHONPATH"]
  copytree(input_path, conf['prefix'])
  assert 0 == call(['ncverilog'] + flags.split(), env=my_env)
  print('pydpi done')
