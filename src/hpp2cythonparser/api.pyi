from pathlib import Path
from typing import overload

@overload
def create_cython_header(
    file_name: Path | str,
    cpp_home: Path | str,
    cython_home: Path | str,
    *,
    show_content: bool = True,
) -> None: ...
@overload
def create_cython_header(
    file_name: Path | str,
    cpp_home: None = None,
    cython_home: None = None,
    show_content: bool = True,
) -> None: ...
