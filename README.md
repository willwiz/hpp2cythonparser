# hpp2cythonparser

Converts a .hpp file to a .pxd file, simplifying the use of c++ in cython. C++ functions and classes can be directly imported from the Cython .pxd header and only an cython interface to the C++ function is needed, resulting in less retyping.

This version will skip all template classes, functions, and functions with template argument. I may consider implementing in the future.

For help, see
```python
hpp2cython -h
```
