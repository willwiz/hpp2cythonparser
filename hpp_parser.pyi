from typing import overload

@overload
def create_cython_header(
    file_name: str,
    cpp_home: str,
    cython_home: str,
    show_content: bool = True,
) -> None: ...
@overload
def create_cython_header(
    file_name: str,
    cpp_home: None = None,
    cython_home: None = None,
    show_content: bool = True,
) -> None: ...
