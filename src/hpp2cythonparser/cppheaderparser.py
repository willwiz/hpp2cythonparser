import os
import re
from glob import glob
import dataclasses as dc
import sys
from typing import Final
from contextlib import contextmanager
from hpp2cythonparser.internals.ctypes import (
    c_generic,
    c_int,
    c_double,
    c_generic_t,
    c_ptr,
    c_void,
    c_constructor,
    c_types,
)
from hpp2cythonparser.internals.tools import (
    remove_comment,
    filterline,
    read_cppfile,
    get_context,
    check_for_semicolon,
    Braces,
)
from hpp2cythonparser.internals.data_types import (
    CPPObject,
    CPPVar,
    CPPFunction,
    CPPClass,
    check_next_type,
    get_variable_type,
)
from hpp2cythonparser.internals.print_headers import (
    print_header,
    print_headers_guard,
    print_end_src,
    print_hppsrc_header,
    print_cppsrc,
)
from hpp2cythonparser.internals.core import (
    find_includes_from_file,
    get_namespace_from_code,
)


@contextmanager
def cwd(path):
    oldpwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)


@dc.dataclass(slots=True)
class InputInfo:
    handle: str
    hpp_file: str
    cpp_file: str
    cython_file: str
    cython_folder: str


_CPP_HOME: Final[str] = os.sep.join(["src", "cpp"])
_CYTHON_HOME: Final[str] = os.sep.join(["src", "cython", "headers"])


def get_variable_instance(code: str) -> tuple[CPPVar, str | None]:
    kind, rest = get_variable_type(code)
    vs, rest = [s.strip() for s in rest.split(";", 1)]
    vs = [v.strip() for v in vs.split(",")]
    array_depth = [v.count("]") for v in vs]
    if array_depth.count(array_depth[0]) != len(array_depth):
        raise ValueError(f"Vars do not have the same type, {vs=}")
    for _ in range(array_depth[0]):
        kind = c_ptr(kind, "[]")
    v_list = [v.split("[")[0] for v in vs]
    rest = check_for_semicolon(rest)
    if rest:
        return CPPVar(kind, ", ".join(v_list)), rest
    return CPPVar(kind, ", ".join(v_list)), None


def format_function_argvar(code: str) -> CPPVar:
    kind, rest = get_variable_type(code)
    array_depth = rest.count("[")
    for _ in range(array_depth):
        kind = c_ptr(kind, "[]")
    name = rest.split("[")[0]
    return CPPVar(kind, name)


def split_function_arguments(code: str) -> list[CPPVar]:
    vs = [v.strip() for v in code.split(",")]
    return [format_function_argvar(v) for v in vs]


def find_function_ending(code: str) -> str:
    function_seperator = re.compile(r";|{};|{}|{\s+};|{\s+}")
    matched_obj = function_seperator.search(code)
    if matched_obj is None:
        raise ValueError("Could not find the end of function")
    return code[matched_obj.end() :].strip()


def get_function_instance(code: str) -> tuple[CPPFunction, str | None]:
    kind, rest = get_variable_type(code)
    match get_context(rest, Braces.round):
        case (name, context, tail):
            fn = CPPFunction(kind, name)
            if context:
                vs = split_function_arguments(context)
                fn.content.extend(vs)
            return (fn, find_function_ending(tail))
        case None:
            raise ValueError(f"Function cannot find context in {code}")


def get_constructor(
    code: str, class_name: str | None
) -> tuple[CPPFunction, str | None]:
    match get_context(code, Braces.round):
        case (name, context, tail):
            if class_name is None:
                raise ValueError(f"Getting constructor but class name is None")
            if class_name != name:
                raise ValueError(f"class {class_name} != {name}")
            fn = CPPFunction(c_constructor(), class_name)
            if context:
                vs = split_function_arguments(context)
                fn.content.extend(vs)
            return fn, find_function_ending(tail)
        case None:
            raise ValueError(f"Function cannot find context in {code}")


def get_destructor(code: str) -> tuple[None, str | None]:
    match get_context(code, Braces.round):
        case (_, _, tail):
            return None, find_function_ending(tail)
        case None:
            raise ValueError(f"Destruction is without call braces")


def get_classmembers_public(code: str) -> str | None:
    start = code.find("public")
    if start < 0:
        return None
    rest = code[start + 6 :].strip()
    start = rest.find(":")
    rest = rest[start + 1 :].strip()
    end = rest.find("private")
    if end > 0:
        return rest[:end]
    end = rest.find("protected")
    if end > 0:
        return rest[:end]
    return rest


def get_class_instance(code: str) -> tuple[CPPClass, str | None]:
    _, name, rest = code.split(None, 2)
    name = name.split(":")[0]
    content = get_context(rest, Braces.curly)
    if content is None:
        raise ValueError(f"Cannot find context for class {name}")
    item = CPPClass(name)
    _, context, tail = content
    context = get_classmembers_public(context)
    while context:
        members, context = getitem_from_code(context, name)
        if isinstance(members, CPPVar | CPPFunction):
            item.content.append(members)
    tail = check_for_semicolon(tail)
    if tail:
        return item, tail
    return item, None


def get_typedef_instance(code: str) -> tuple[None, str | None]:
    first = code.find(";")
    return None, code[first + 1 :]


def get_inline_instance(code: str) -> tuple[None, str | None]:
    _, rest = code.split(None, 2)
    _, tail = getitem_from_code(rest)
    return None, tail


def get_template_instance(code: str) -> tuple[None, str | None]:
    match get_context(code, Braces.angle):
        case (_, _, rest):
            _, tail = getitem_from_code(rest)
            return None, tail
        case None:
            raise ValueError(f"Cannot found template parameter part for template.")


def valid_function_arg(v_type: c_types) -> bool:
    match v_type:
        case c_ptr():
            valid_function_arg(v_type.kind)
        case c_void() | c_int() | c_double() | c_generic():
            pass
        case c_generic_t():
            print(f">>>>WARNING: template function args not implemented, {v_type=}")
            return False
        case _:
            print(f">>>>WARNING: inadmissible type {v_type}, ignored")
            return False
    return True


def function_arg_check(fn: CPPFunction) -> CPPFunction | None:
    print(fn)
    for v in fn.content:
        if not valid_function_arg(v.kind):
            return None
    return fn


def getitem_from_code(
    code: str, class_name: str | None = None
) -> tuple[CPPVar | CPPFunction | CPPClass | None, str | None]:
    kind = check_next_type(code, class_name)
    match kind:
        case CPPObject.cls:
            return get_class_instance(code)
        case CPPObject.var:
            return get_variable_instance(code)
        case CPPObject.func:
            member, rest = get_function_instance(code)
            return function_arg_check(member), rest
        case CPPObject.constructor:
            member, rest = get_constructor(code, class_name)
            return function_arg_check(member), rest
        case CPPObject.destructor:
            return get_destructor(code)
        case CPPObject.typedef:
            return get_typedef_instance(code)
        case CPPObject.template:
            return get_template_instance(code)
        case _:
            raise ValueError("To Be implemented")


def parse_cppheader_code(code: str) -> list[CPPVar | CPPFunction | CPPClass]:
    rest = code
    content: list[CPPVar | CPPFunction | CPPClass] = list()
    while rest:
        item, rest = getitem_from_code(rest)
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
        fout.write(print_header(inp.handle))
        for s in includes:
            fout.write(f"cimport {s}\n")
        fout.write("\n")
        if os.path.isfile(inp.cpp_file):
            fout.write(print_cppsrc(inp.cpp_file))
        fout.write(print_end_src())
        fout.write(print_headers_guard())
        fout.write(print_hppsrc_header(inp.hpp_file, namespace))
        if show_content and (content != []):
            for c in content:
                fout.write(c.to_string())
                fout.write("\n\n")
        else:
            fout.write("  pass")


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
        cython_folder = folder
    cpp_file = hpp_file.replace(".hpp", ".cpp")
    cython_file = os.path.join(cython_folder, handle + ".pxd")
    return InputInfo(handle, hpp_file, cpp_file, cython_file, cython_folder)


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


def main():
    with cwd(os.path.dirname(__file__)):
        files = glob("src/cpp/*/*.hpp")
        for fin in files:
            create_cython_header(fin)
        files = glob("src/cpp/*.hpp")
        for fin in files:
            create_cython_header(fin)


if __name__ == "__main__":
    # create_cython_header(sys.argv[1])
    # main(show_content=True)
    create_cython_header(sys.argv[1])
    # files = glob('src/cpp/kernel_density_estimation/*.hpp')
    # for fin in files:
    #     print(f"Working on {fin}")
    #     main(fin)
