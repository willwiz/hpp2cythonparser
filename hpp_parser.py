import os
import dataclasses as dc
import sys
from internals.tools import remove_comment, filterline, read_cppfile
from internals.data_types import CPPVar, CPPFunction, CPPClass
from internals import print_headers as hp
from internals.core import (
    find_includes_from_file,
    get_namespace_from_code,
    get_item_from_code,
)


@dc.dataclass(slots=True)
class InputInfo:
    handle: str
    hpp_file: str
    cpp_file: str
    cython_file: str
    cython_folder: str


def get_input_info(
    file_name: str,
    cpp_home: str | None = None,
    cython_home: str | None = None,
) -> InputInfo:
    hpp_file = os.path.normpath(file_name)
    folder, name = os.path.split(hpp_file)
    handle, _ = os.path.splitext(name)
    if cpp_home and cython_home:
        cython_folder = folder.replace(cpp_home, cython_home)
    else:
        cython_folder = "."
    cpp_file = hpp_file.replace(".hpp", ".cpp")
    cython_file = os.path.join(cython_folder, handle + ".pxd")
    return InputInfo(handle, hpp_file, cpp_file, cython_file, cython_folder)


def parse_cppheader_code(code: str) -> list[CPPVar | CPPFunction | CPPClass]:
    rest = code
    content: list[CPPVar | CPPFunction | CPPClass] = list()
    while rest:
        item, rest = get_item_from_code(rest)
        if item is not None:
            content.append(item)
        print(f"{content=}")
    return content


def export_cython_header(
    inp: InputInfo,
    includes: list[str],
    namespace: str | None,
    content: list[CPPVar | CPPFunction | CPPClass],
    show_content: bool,
) -> None:
    os.makedirs(os.path.dirname(inp.cython_file), exist_ok=True)
    with open(inp.cython_file, "w") as fout:
        fout.write(hp.print_header(inp.handle))
        for s in includes:
            fout.write(f"cimport {s}\n")
        fout.write("\n")
        if os.path.isfile(inp.cpp_file):
            fout.write(hp.print_cppsrc(inp.cpp_file))
        fout.write(hp.print_end_src())
        fout.write(hp.print_headers_guard())
        fout.write(hp.print_hppsrc_header(inp.hpp_file, namespace))
        if show_content and (content != []):
            for c in content:
                fout.write(c.to_string())
                fout.write("\n\n")
        else:
            fout.write("  pass")


def create_cython_header(
    file_name: str,
    show_content: bool = True,
    cpp_home: str | None = None,
    cython_home: str | None = None,
) -> None:
    inp = get_input_info(file_name, cpp_home, cython_home)
    print(f"{inp.cython_file=}")
    includes_cpp = (
        find_includes_from_file(inp.cpp_file, inp.handle + ".hpp", inp.cython_folder)
        if os.path.isfile(inp.cpp_file)
        else list()
    )
    includes_hpp = find_includes_from_file(
        inp.hpp_file, inp.handle + ".hpp", inp.cython_folder
    )
    includes = sorted(list(set(includes_cpp + includes_hpp)))

    namespace, code = get_namespace_from_code(
        remove_comment(filterline(read_cppfile(inp.hpp_file), "#include"))
    )
    content = parse_cppheader_code(code)
    print(f"{includes=}")
    print(f"{namespace=}")
    print([s.name for s in content], "\n")
    export_cython_header(inp, includes, namespace, content, show_content)


if __name__ == "__main__":
    create_cython_header(sys.argv[1])
