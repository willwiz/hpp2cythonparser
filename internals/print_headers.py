from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def print_header(hand: str) -> str:
    return f'''\
# File: {hand}.pxd
# distutils: language = c++
# cython: language_level=3


""" ----------------------------------------------------------------------------
C++ Source Files
---------------------------------------------------------------------------- """

'''


def print_end_src() -> str:
    return '''\

""" ----------------------------------------------------------------------------
End of Source Files
---------------------------------------------------------------------------- """

'''


def print_headers_guard() -> str:
    return """\

# ------------------------------------------------------------------------------
# C++ Header files + exported definitions
# ------------------------------------------------------------------------------

"""


def print_cppsrc(src: Path | str) -> str:
    return f"""
cdef extern from r"{src}":
  pass
"""


def print_hppsrc_header(src: Path | str, namespace: str | None = None) -> str:
    if namespace is None:
        return f'cdef extern from r"{src}":'
    return f'cdef extern from r"{src}" namespace "{namespace}":\n'
