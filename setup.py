# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path
import fnmatch
import os

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
  long_description = f.read()

# recursively find **.c under pydpi/src
dpi_srcs = []
for root, dirnames, filenames in os.walk('pydpi/src'):
  for filename in fnmatch.filter(filenames, '*.c'):
    dpi_srcs.append(os.path.join(root, filename).replace('pydpi/',''))

setup(
  name='python-svlog',

  # Versions should comply with PEP440.  For a discussion on single-sourcing
  # the version across setup.py and the project code, see
  # https://packaging.python.org/en/latest/single_source_version.html
  version='0.1.0',

  description='Verilog development framework with DPI-python verification utils',
  long_description=long_description,

  # The project's main homepage.
  url='https://github.com/hchsiao/python-svlog',

  # Author details
  author='Hsiang-Chih Hsiao',
  author_email='hchsiao@vlsilab.ee.ncku.edu.tw',

  # Choose your license
  license='MIT',

  # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
  classifiers=[
    # How mature is this project? Common values are
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    'Development Status :: 2 - Pre-Alpha',

    # Indicate who your project is intended for
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Code Generators',

    # Pick your license as you wish (should match "license" above)
    'License :: OSI Approved :: MIT License',

    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
  ],

  # What does your project relate to?
  keywords='sample setuptools development',

  # You can just specify the packages manually here if your project is
  # simple. Or you can use find_packages().
  packages=find_packages(exclude=['contrib', 'docs', 'tests']),

  # Alternatively, if you want to distribute just a my_module.py, uncomment
  # this:
  #   py_modules=["my_module"],

  # List run-time dependencies here.  These will be installed by pip when
  # your project is installed. For an analysis of "install_requires" vs pip's
  # requirements files see:
  # https://packaging.python.org/en/latest/requirements.html
  install_requires=['anyconfig'],

  # If there are data files included in your packages that need to be
  # installed, specify them here.  If using Python 2.6 or less, then these
  # have to be included in MANIFEST.in as well.
  package_data={
    'pydpi': ['templates/*'] + dpi_srcs,
  },
  data_files=[
      ('.', ['LICENSE']),
      ],

  # To provide executable scripts, use entry points in preference to the
  # "scripts" keyword. Entry points provide cross-platform support and allow
  # pip to create the appropriate form of executable for the target platform.
  entry_points={
    'console_scripts': [
      'pydpi-gen = pydpi.utils:run_gen',
      'pydpi-gen-mod = pydpi.utils:run_gen_mod',
      'pydpi-gen-param = pydpi.utils:run_gen_param',
      'pydpi-build = pydpi.utils:run_build_bridge',
      'pydpi-run = pydpi.utils:run_run',
    ],
  },
)
