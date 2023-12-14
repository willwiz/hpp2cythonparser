def print_header(hand: str) -> str:
    return f'''\
# File: {hand}.pxd
# distutils: language = c++
# cython: language_level=3


""" ----------------------------------------------------------------------------
C++ Source Files
---------------------------------------------------------------------------- """

'''


def print_end_src():
    return '''\

""" ----------------------------------------------------------------------------
End of Source Files
---------------------------------------------------------------------------- """

'''


def print_headers_guard():
    return """\

# ------------------------------------------------------------------------------
# C++ Header files + exported definitions
# ------------------------------------------------------------------------------

"""


def print_cppsrc(src: str):
    return f"""\
cdef extern from "{src}":
  pass
"""


def print_hppsrc_header(src: str, namespace: str | None = None):
    if namespace is None:
        return f'cdef extern from "{src}":'
    return f'cdef extern from "{src}" namespace "{namespace}":\n'
