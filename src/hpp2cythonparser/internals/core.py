import os
from hpp2cythonparser.internals.tools import (
    read_cppfile,
    get_context,
)
from hpp2cythonparser.internals.data_types import Braces


def parse_include(code: str, exclude: str, folder: str) -> str | None:
    splitted_code = code.split()
    if len(splitted_code) != 2:
        raise ValueError(f"Improper header line: {code}")
    _, header = splitted_code
    if header.startswith('"') and header.endswith('"'):
        _, string = os.path.split(header.replace('"', "").strip())
        if string != exclude:
            string = os.path.join(folder, header.replace('"', ""))
            string, _ = os.path.splitext(os.path.normpath(string))
            return ".".join(string.split(os.sep))
    return None


def find_includes_from_file(name: str, header: str, folder: str) -> list[str]:
    code = read_cppfile(name)
    header_lines = [
        parse_include(line, header, folder)
        for line in code
        if line.startswith("#include")
    ]
    return [line for line in header_lines if line]


def get_namespace_from_code(code: str) -> tuple[str | None, str]:
    raw_code = code
    n_namespace = raw_code.count("namespace")
    if n_namespace > 1:
        raise ValueError(
            "This code currently only works with up to one namespace per file"
        )
    elif n_namespace == 1:
        start = raw_code.find("namespace")
        namespace, rest = raw_code[start + 9 :].split(None, 1)
        match get_context(rest, Braces.curly):
            case (head, raw, tail):
                return namespace, raw.strip()
            case None:
                raise ValueError(f"Cannot find context for namespace {namespace}")
    return None, raw_code
