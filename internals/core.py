import os
import re
from tools import (
    Braces,
    read_cppfile,
    get_context,
    check_for_semicolon,
)
from c_types import (
    c_generic,
    c_int,
    c_double,
    c_generic_t,
    c_ptr,
    c_void,
    c_constructor,
    c_types,
)
from data_types import (
    CPPObject,
    CPPVar,
    CPPFunction,
    CPPClass,
    check_next_type,
    get_variable_type,
)


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
        members, context = get_item_from_code(context, name)
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
    _, tail = get_item_from_code(rest)
    return None, tail


def get_template_instance(code: str) -> tuple[None, str | None]:
    match get_context(code, Braces.angle):
        case (_, _, rest):
            _, tail = get_item_from_code(rest)
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


def get_item_from_code(
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
