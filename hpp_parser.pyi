from typing import overload

@overload
def create_cython_header(
    file_name: str,
    cpp_home: str,
    cython_home: str,
    show_content: bool = True,
) -> None:
    """
    Creates a cython header file (.pyx) from cpp header files.

    Args:
        file_name (str): the relative or absolute path to the cpp header file to be converted.
        cpp_home (str): the home directory of the cpp files
        cython_home (str): the home directory of the cython headers to be outputed, this will replace the cpp_home str
        show_content (boo): whether to print the element of the AST for the Header
    """
    ...

@overload
def create_cython_header(
    file_name: str,
    cpp_home: None = None,
    cython_home: None = None,
    show_content: bool = True,
) -> None: ...
