#include <Python.h>
#include <svdpi.h>

#define PY_MOD "pydpi.dispatch"
#define PY_FUNC_DESTROY "_Destroy"
#define PY_FUNC_TRIGGER "_Eval"
#define PY_FUNC_SET "_Set"
#define PY_FUNC_GET "_Get"

PyObject *pModule, *pFuncDestroy, *pFuncTrigger, *pFuncGet, *pFuncSet;
static uint8_t init_flag = 0;

void PyDPI_destroy() {
  PyObject *pArgs;
  pArgs = PyTuple_New(0);
  PyObject_CallObject(pFuncDestroy, pArgs);
  Py_DECREF(pArgs);

  Py_XDECREF(pFuncTrigger);
  Py_XDECREF(pFuncDestroy);
  Py_XDECREF(pFuncGet);
  Py_XDECREF(pFuncSet);
  Py_DECREF(pModule);
  Py_Finalize();
  printf("DPI bridge destroied\n");
}

void PyDPI_init() {
  if(init_flag)
    return;

  PyObject *pName;
  Py_Initialize();
  pName = PyString_FromString(PY_MOD);
  pModule = PyImport_Import(pName);
  Py_DECREF(pName);
  if (pModule != NULL) {
    pFuncDestroy = PyObject_GetAttrString(pModule, PY_FUNC_DESTROY);
    pFuncTrigger = PyObject_GetAttrString(pModule, PY_FUNC_TRIGGER);
    pFuncGet = PyObject_GetAttrString(pModule, PY_FUNC_GET);
    pFuncSet = PyObject_GetAttrString(pModule, PY_FUNC_SET);
  }
  else {
    PyErr_Print();
    fprintf(stderr, "Failed to load \"%s\"\n", PY_MOD);
    PyDPI_destroy();
    return;
  }
  if (
      !pFuncTrigger || !PyCallable_Check(pFuncTrigger) ||
      !pFuncGet || !PyCallable_Check(pFuncGet) ||
      !pFuncSet || !PyCallable_Check(pFuncSet)
  ) {
    if (PyErr_Occurred())
      PyErr_Print();
    fprintf(stderr, "Cannot find function \"%s\"\n", PY_FUNC_TRIGGER);
    PyDPI_destroy();
    return;
  }

  init_flag = 1;
  printf("DPI initialized\n");
}

void PyDPI_eval(uint8_t func_id) {
  PyObject *pArgs, *pValue;

  pArgs = PyTuple_New(1);
  pValue = PyInt_FromLong(func_id);
  PyTuple_SetItem(pArgs, 0, pValue);

  PyObject_CallObject(pFuncTrigger, pArgs);
  Py_DECREF(pArgs);
}

void PyDPI_buf_write(uint8_t func_id, uint8_t addr, uint8_t data) {
  PyObject *pArgs, *pValue;

  pArgs = PyTuple_New(3);
  pValue = PyInt_FromLong(func_id);
  PyTuple_SetItem(pArgs, 0, pValue);
  pValue = PyInt_FromLong(addr);
  PyTuple_SetItem(pArgs, 1, pValue);
  pValue = PyInt_FromLong(data);
  PyTuple_SetItem(pArgs, 2, pValue);

  PyObject_CallObject(pFuncSet, pArgs);
  Py_DECREF(pArgs);
}

uint8_t PyDPI_buf_read(uint8_t func_id, uint8_t addr) {
  PyObject *pArgs, *pValue;
  uint8_t retval = 0;

  pArgs = PyTuple_New(2);
  pValue = PyInt_FromLong(func_id);
  PyTuple_SetItem(pArgs, 0, pValue);
  pValue = PyInt_FromLong(addr);
  PyTuple_SetItem(pArgs, 1, pValue);

  pValue = PyObject_CallObject(pFuncGet, pArgs);
  Py_DECREF(pArgs);

  if (pValue != NULL) {
    // printf("Result of call: %ld\n", PyInt_AsLong(pValue));
    retval = PyInt_AsLong(pValue);
    Py_DECREF(pValue);
  }
  else {
    PyErr_Print();
    fprintf(stderr,"Call failed\n");
  }
  return retval;
}
