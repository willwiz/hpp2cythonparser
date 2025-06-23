from __future__ import annotations

__all__ = [
    "export_cython_header",
    "find_includes_from_file",
    "get_input_info",
    "parse_cppheader_code",
]

import dataclasses as dc
from pathlib import Path
from typing import TYPE_CHECKING

from . import print_headers as hp
from .file_parsing import get_item_from_code, parse_include
from .tools import Braces, get_context, read_cppfile

if TYPE_CHECKING:
    from pytools.logging.trait import ILogger

    from hpp2cythonparser.struct import CPPClass, CPPFunction, CPPVar


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


def find_includes_from_file(name: Path | str, header: str, folder: Path | str) -> list[str]:
    code = read_cppfile(name)
    header_lines = [
        parse_include(line, header, folder) for line in code if line.startswith("#include")
    ]
    return [line for line in header_lines if line]


def get_namespace_from_code(code: str) -> tuple[str | None, str]:
    raw_code = code
    n_namespace = raw_code.count("namespace")
    if n_namespace > 1:
        msg = f">>>ERROR: found {n_namespace} namespaces in code, expected 1"
        raise ValueError(msg)
    if n_namespace == 1:
        start = raw_code.find("namespace")
        namespace, rest = raw_code[start + 9 :].split(None, 1)
        match get_context(rest, Braces.curly):
            case str(), str(raw), str():
                return namespace, raw.strip()
            case None:
                msg = f">>>ERROR: cannot find context for namespace {namespace}"
                raise ValueError(msg)
    return None, raw_code


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
