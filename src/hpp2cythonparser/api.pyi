__all__ = ["create_cython_header"]
from pathlib import Path
from typing import overload

from pytools.logging.trait import ILogger

@overload
def create_cython_header(
    file_name: Path | str,
    cpp_home: Path | str,
    cython_home: Path | str,
    log: ILogger = ...,
    *,
    show_content: bool = True,
) -> None: ...
@overload
def create_cython_header(
    file_name: Path | str,
    cpp_home: None = None,
    cython_home: None = None,
    log: ILogger = ...,
    *,
    show_content: bool = True,
) -> None: ...
