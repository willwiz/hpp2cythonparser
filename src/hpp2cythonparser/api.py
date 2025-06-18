from __future__ import annotations

from pprint import pformat

__all__ = [
    "create_cython_header",
]

import dataclasses as dc
from pathlib import Path
from typing import TYPE_CHECKING

from pytools.logging.api import NULL_LOGGER

from .internals import print_headers as hp
from .internals.core import (
    find_includes_from_file,
    get_item_from_code,
    get_namespace_from_code,
)
from .internals.tools import filterline, read_cppfile, remove_comment

if TYPE_CHECKING:
    from pytools.logging.trait import ILogger

    from .internals.data_types import CPPClass, CPPFunction, CPPVar


@dc.dataclass(slots=True)
class InputInfo:
    hpp_file: Path
    cpp_file: Path
    cython_file: Path
    cython_folder: Path


def get_input_info(
    file_name: Path | str,
    log: ILogger,
    cpp_home: Path | str | None = None,
    cython_home: Path | str | None = None,
) -> InputInfo:
    hpp_file = Path(file_name)
    cython_folder = (
        Path(cython_home) / hpp_file.parent.relative_to(cpp_home)
        if cpp_home and cython_home
        else Path()
    )
    cpp_file = hpp_file.with_suffix(".cpp")
    cython_file = cython_folder / hpp_file.with_suffix(".pxd").name
    log.info(
        f"Processing header {hpp_file} with source file",
        f"  hpp name is {hpp_file.with_suffix('.pxd').name}",
        f"  {cpp_file}",
        f"  the cython header will be saved to {cython_file}",
    )
    return InputInfo(hpp_file, cpp_file, cython_file, cython_folder)


def parse_cppheader_code(code: str, log: ILogger) -> list[CPPVar | CPPFunction | CPPClass]:
    rest = code
    content: list[CPPVar | CPPFunction | CPPClass] = []
    while rest:
        item, rest = get_item_from_code(rest, log)
        if item is not None:
            content.append(item)
    return content


def export_cython_header(
    inp: InputInfo,
    includes: list[str],
    namespace: str | None,
    content: list[CPPVar | CPPFunction | CPPClass],
    *,
    show_content: bool,
) -> None:
    inp.cython_file.parent.mkdir(parents=True, exist_ok=True)
    with inp.cython_file.open("w") as fout:
        fout.write(hp.print_header(inp.hpp_file.stem))
        for s in includes:
            fout.write(f"cimport {s}\n")
        fout.write("\n")
        if inp.cpp_file.is_file():
            fout.write(hp.print_cppsrc(inp.cpp_file))
        fout.write(hp.print_end_src())
        fout.write(hp.print_headers_guard())
        fout.write(hp.print_hppsrc_header(inp.hpp_file, namespace))
        if show_content and (content != []):
            for c in content:
                fout.write(str(c))
                fout.write("\n\n")
        else:
            fout.write("  pass")


def create_cython_header(
    file_name: Path | str,
    cpp_home: Path | str | None = None,
    cython_home: Path | str | None = None,
    log: ILogger = NULL_LOGGER,
    *,
    show_content: bool = True,
) -> None:
    inp = get_input_info(file_name, log, cpp_home, cython_home)

    includes_cpp: list[str] = (
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
