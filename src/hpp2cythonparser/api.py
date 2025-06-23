from __future__ import annotations

__all__ = ["create_cython_header"]
from pprint import pformat
from typing import TYPE_CHECKING

from pytools.logging.api import NULL_LOGGER, ILogger

from ._internals.core import (
    export_cython_header,
    find_includes_from_file,
    get_input_info,
    get_namespace_from_code,
    parse_cppheader_code,
)
from ._internals.tools import filterline, read_cppfile, remove_comment

if TYPE_CHECKING:
    from pathlib import Path


def create_cython_header(
    file_name: Path | str,
    cpp_home: Path | str | None = None,
    cython_home: Path | str | None = None,
    log: ILogger = NULL_LOGGER,
    *,
    show_content: bool = True,
) -> None:
    inp = get_input_info(file_name, log, cpp_home, cython_home)

    includes_cpp = (
        find_includes_from_file(inp.cpp_file, inp.hpp_file.name, inp.cython_folder)
        if inp.cpp_file.is_file()
        else []
    )
    includes_hpp = find_includes_from_file(
        inp.hpp_file,
        inp.hpp_file.name,
        inp.cython_folder,
    )
    includes = sorted(set(includes_cpp + includes_hpp))
    namespace, code = get_namespace_from_code(
        remove_comment(filterline(read_cppfile(inp.hpp_file), "#include")),
    )
    content = parse_cppheader_code(code, log)
    log.info(f"The header name is {namespace}")
    log.info(
        f"Includes found: {len(includes)} items, ",
        pformat(includes),
    )
    log.info(
        f"Content found: {len(content)} items, ",
        pformat(content),
        "\n",
    )
    export_cython_header(inp, includes, namespace, content, show_content=show_content)
