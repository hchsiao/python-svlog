import os.path
import subprocess
import shutil
import anyconfig

this_dir, this_filename = os.path.split(__file__)
tmpl_dir = os.path.join(this_dir, "templates/")
home_dir = os.path.expanduser('~')
config_file = os.path.join(home_dir, '.python-svlog-cfg')
config_file = 'svlog-cfg.json' # TODO: use multi config files
if not os.path.isfile(config_file):
  pretty_json = {
      'sort_keys': True,
      'indent': 2,
      'separators': (',', ': '),
      }
  anyconfig.dump({
    'env': {
      'input_path': './src/',
      'prefix': 'cache/',
      'dpi_inc': '/opt/Cadence/INCISIV/cur/tools/include',
      'py_cfg': 'python-config',
      'cc': 'gcc',
      },
    'params': {
      'EXAMPLE_PARAM': 5
      },
    }, config_file, 'json', **pretty_json)
  print('Created {} since it does not exist. Please fill the fields and re-run'.format(config_file))
  exit(1)
else:
  conf = anyconfig.load(config_file, 'json')['env']
  input_path = conf['input_path']
  prefix = conf['prefix']
  py_prefix = os.path.join(prefix, 'python/')
  sv_prefix = os.path.join(prefix, 'svlog/')

CC = conf['cc']
FILE_SIZE_LMT = 1000000 # 1 MiB
PYDPI_FILE_FEAT_STR_FUNC = 'pydpi.export'
PYDPI_FILE_FEAT_STR_MOD = 'pydpi.SvModule'
PYDPI_PARAM_NAME_RETVAL = 'retval_width'
PYDPI_PARAM_NAME_PARAM = 'params_width'
PYDPI_SYS_WORD_IN = 'input [{msb}:0] pydpi_arg{idx};'
PYDPI_SYS_WBUF = 'PyDPI_buf_write(PYDPI_FUNC_{func_name}, {buf_addr}, {{{data}}});'
PYDPI_SYS_RBUF = 'tmp = PyDPI_buf_read(PYDPI_FUNC_{func_name}, {buf_addr});'
PYDPI_SYS_FLUSH = '{func_name}[{retval_msb}:{retval_lsb}] = tmp[{msb}:{lsb}];'
PYDPI_SYS_DEFINE_PARAM = '`define {param_name} {param_val}'
def is_candidate_file(fname, feat_str=None, prefix=None):
  prefix = input_path if prefix is None else prefix
  fpath = prefix + fname
  if not os.path.isfile(fpath):
    return False
  elif fname[0] == '.':
    return False
  elif fname[-3:] != '.py':
    return False
  elif os.path.getsize(fpath) > FILE_SIZE_LMT:
    return False
  else:
    if not feat_str is None:
      src = open(fpath).read()
      if not feat_str in src:
        return False
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

def gen(tmpl_fname, params=None, prefix=None):
  tmpl_file = open(tmpl_dir + tmpl_fname + '.tmpl')
  tmpl = tmpl_file.read()

  params = {} if params is None else params
  prefix = prefix if prefix is None else prefix
  fname = tmpl_fname.format(**params)
  f = open(os.path.join(prefix, fname), 'w')
  f.write(tmpl.format(**params))
  f.close()

def run_gen():
  import string
  import ast

  gen('pydpi_gen_common.sv', prefix=sv_prefix)

  # code-gen for intermediate codes store in py_prefix
  input_path = py_prefix

  registration_str = ''
  func_file_list = [fn[:-3] for fn in os.listdir(input_path) if is_candidate_file(fn, PYDPI_FILE_FEAT_STR_FUNC, py_prefix)]
  registration_str += string.join(['import ' + fn for fn in func_file_list], '\n')
  registration_str += '\nimport pydpi\n'
  registration_str += string.join(['pydpi.__reg_mod(' + fn + ')' for fn in func_file_list], '\n')
  gen('pydpi_gen_registration.py', params={
    'registration_str': registration_str,
    }, prefix=py_prefix)

  func_specs = {}
  for fn in func_file_list:
    src = open(input_path + fn + '.py').read().split('\n')
    export_statements = [line for line in src if PYDPI_FILE_FEAT_STR_FUNC in line]
    for stmnt in export_statements:
      args = stmnt.replace(PYDPI_FILE_FEAT_STR_FUNC, '')
      arg_tuple = args.replace('=', '').replace(' ', '').replace(PYDPI_PARAM_NAME_RETVAL, '"{}",'.format(PYDPI_PARAM_NAME_RETVAL)).replace(PYDPI_PARAM_NAME_PARAM, '"{}",'.format(PYDPI_PARAM_NAME_PARAM))
      arg_tuple = ast.literal_eval(arg_tuple)
      func_name = arg_tuple[0]
      for i in [1, 3]:
        argn = arg_tuple[i]
        argv = arg_tuple[i+1]
        if argn == PYDPI_PARAM_NAME_RETVAL:
          retval_width = argv
        elif argn == PYDPI_PARAM_NAME_PARAM:
          params_width = argv
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
    gen('pydpi_gen_func_{func_name}.sv', params={
      'func_name': func_name,
      'retval_msb': out_width-1,
      'decl_input': decl_input.strip(),
      'stmnt_wbuf': stmnt_wbuf.strip(),
      'stmnt_rbuf': stmnt_rbuf.strip(),
      }, prefix=sv_prefix)

def run_gen_param():
  import string
  import pydpi
  params = pydpi.get_params()
  params_str = [PYDPI_SYS_DEFINE_PARAM.format(**{
    'param_name': param_name,
    'param_val': params[param_name],
    }) for param_name in params.keys()]
  gen('pydpi_gen_params.sv', params={
    'params_str': string.join(params_str, '\n')
    }, prefix=sv_prefix)

def run_gen_mod():
  import importlib
  import sys
  import string
  if not os.path.exists(prefix):
    os.mkdir(prefix)
  if not os.path.exists(py_prefix):
    os.mkdir(py_prefix)
  if not os.path.exists(sv_prefix):
    os.mkdir(sv_prefix)

  import pydpi
  sys.path.insert(0, py_prefix)

  mod_file_list = [fn[:-3] for fn in os.listdir(input_path) if is_candidate_file(fn, PYDPI_FILE_FEAT_STR_MOD)]
  for fn in mod_file_list:
    shutil.copy(os.path.join(input_path, fn+'.py'), py_prefix)
    _mod = importlib.import_module(fn)
    _mod_class = getattr(_mod, fn)
    io_spec = _mod_class.io_spec

    ports_str = ''
    for port_name in io_spec:
      port_type, port_width = io_spec[port_name]
      if port_type == pydpi.PORT_OUTPUT:
        type_str = 'output wire'
      elif port_type == pydpi.PORT_OUTPUT_REG:
        type_str = 'output reg'
      elif port_type == pydpi.PORT_INPUT:
        type_str = 'input wire'
      elif port_type == pydpi.PORT_INPUT_CLOCK:
        type_str = 'input wire'
      else:
        assert False
      width_str = '[{}:0]'.format(port_width - 1)
      port_str = '{} {} {},\n'.format(type_str, width_str, port_name)
      ports_str += port_str
    ports_str = ports_str[:-2]

    func_declarations = ''
    assigns_str = ''
    state_update_str = ''
    py_func_str = ''
    for port_name in io_spec:
      port_type, port_width = io_spec[port_name]
      if port_type == pydpi.PORT_OUTPUT or port_type == pydpi.PORT_OUTPUT_REG:
        if hasattr(_mod_class, port_name):
          _method = getattr(_mod_class, port_name)
          _arg_names = _method.im_func.func_code.co_varnames
          _i_names = _arg_names[1:] # w/o 'self' argument
          _i_widths = [io_spec[p_name][1] for p_name in _i_names]
          _i_widths_str = [str(p_width) for p_width in _i_widths]
          i_ports_str = string.join(_i_names, ', ')
          i_ports_width = string.join(_i_widths_str, ', ')+',' # to be interpreted as tuple
        else:
          print('missing output method!')
          assert False
        func_declarations += '`include "pydpi_gen_func__pydpi_mod_{}_func_{}.sv"\n'.format(fn, port_name)
        py_func_str += ('pydpi.export("_pydpi_mod_{0}_func_{1}", retval_width={2}, params_width=({3}))\n'
          + 'def _pydpi_mod_{0}_func_{1}({4}):\n'
          + '  return _inst.{1}({4})\n\n').format(fn, port_name, port_width, i_ports_width, i_ports_str)

      if port_type == pydpi.PORT_OUTPUT:
        assigns_str += 'assign {1} = _pydpi_mod_{0}_func_{1}({2});\n'.format(fn, port_name, i_ports_str)
      elif port_type == pydpi.PORT_OUTPUT_REG:
        state_update_str += '{1} <= _pydpi_mod_{0}_func_{1}({2});\n'.format(fn, port_name, i_ports_str)

    func_declarations = func_declarations[:-1]
    assigns_str = assigns_str[:-1]
    state_update_str = state_update_str[:-1]

    gen('pydpi_gen_mod_{mod_name}.sv', params={
      'mod_name': fn,
      'ports_str': ports_str,
      'func_declarations': func_declarations,
      'assigns_str': assigns_str,
      'state_update_str': state_update_str,
      }, prefix=sv_prefix)
    gen('pydpi_gen_funcs_{mod_name}.py', params={
      'mod_name': fn,
      'py_func_str': py_func_str,
      }, prefix=py_prefix)


def run_build_bridge():
  kwargs = {
      'in_file': os.path.join(this_dir, 'src/bridge/ies/pydpi_bridge.c'),
      'out_file': os.path.join(prefix, 'pydpi_bridge.so'),
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
  flags = '+nc64bit +sv +sv_lib=./cache/pydpi_bridge.so +access+r +incdir+"./cache/svlog" -mccodegen src/test.sv'.format(**kwargs)
  my_env = os.environ.copy()
  my_env["PYTHONPATH"] = "./cache/python:" + my_env["PYTHONPATH"]
  #copytree(input_path, prefix)
  assert 0 == call(['ncverilog'] + flags.split(), env=my_env)
  print('pydpi done')
