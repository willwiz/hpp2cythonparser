from __future__ import annotations

import os
import re
from pathlib import Path

from .c_types import (
    Ctype,
    c_constructor,
    c_double,
    c_generic,
    c_generic_t,
    c_int,
    c_ptr,
    c_void,
)
from .data_types import (
    CPPClass,
    CPPFunction,
    CPPObject,
    CPPVar,
    check_next_type,
    get_variable_type,
)
from .tools import (
    Braces,
    check_for_semicolon,
    get_context,
    read_cppfile,
)

_INCLUDE_SIZE = 2


def parse_include(code: str, exclude: str, folder: Path | str) -> str | None:
    splitted_code = [s.strip() for s in code.strip().split()]
    # print(f"{splitted_code=}")
    if len(splitted_code) != _INCLUDE_SIZE:
        msg = f">>>ERROR: improper header line: {code}"
        raise ValueError(msg)
    _, string = splitted_code
    if not (string.startswith('"') and string.endswith('"')):
        return None
    header = Path(string.replace('"', "").strip())
    if header.name == exclude:
        return None
    return ".".join(Path(os.path.normpath(str((folder / header).with_suffix("")))).parts)


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


def get_variable_instance(code: str, *, nested: bool = False) -> tuple[CPPVar, str | None]:
    kind, rest = get_variable_type(code)
    vs, rest = [s.strip() for s in rest.split(";", 1)]
    vs = [v.strip() for v in vs.split(",")]
    array_depth = [v.count("]") for v in vs]
    if array_depth.count(array_depth[0]) != len(array_depth):
        msg = f">>>ERROR: vars do not have the same array depth, {vs=}"
        raise ValueError(msg)
    if array_depth[0] > 0:
        kind = c_ptr(kind, f"[{','.join([':' for _ in range(array_depth[0])])}]")
    v_list = [v.split("=")[0] for v in vs]
    v_list = [v.split("[")[0] for v in v_list]
    rest = check_for_semicolon(rest)
    if rest:
        return CPPVar(kind, ", ".join(v_list), nested), rest
    return CPPVar(kind, ", ".join(v_list), nested), None


def format_function_argvar(code: str, *, subelem: bool) -> CPPVar:
    kind, rest = get_variable_type(code)
    array_depth = rest.count("[")
    for _ in range(array_depth):
        kind = c_ptr(kind, "[]")
    name = rest.split("[")[0]
    return CPPVar(kind, name, subelem)


def split_function_arguments(code: str, *, subelem: bool = False) -> list[CPPVar]:
    vs = [v.strip() for v in code.split(",")]
    return [format_function_argvar(v, subelem=subelem) for v in vs]


def find_function_ending(code: str) -> str:
    function_seperator = re.compile(r";|{};|{}|{\s+};|{\s+}")
    matched_obj = function_seperator.search(code)
    if matched_obj is None:
        msg = f">>>ERROR: cannot find function ending in code: {code}"
        raise ValueError(msg)
    return code[matched_obj.end() :].strip()


def get_function_instance(code: str, *, nested: bool = False) -> tuple[CPPFunction, str | None]:
    kind, rest = get_variable_type(code)
    match get_context(rest, Braces.round):
        case (name, context, tail):
            fn = CPPFunction(kind, name, _subelem=nested)
            if context:
                vs = split_function_arguments(context, subelem=True)
                fn.content.extend(vs)
            return (fn, find_function_ending(tail))
        case None:
            msg = f">>>ERROR: function {code} does not have context braces"
            raise ValueError(msg)


def get_constructor(
    code: str,
    class_name: str | None,
    *,
    nested: bool = False,
) -> tuple[CPPFunction, str | None]:
    match get_context(code, Braces.round):
        case (name, context, tail):
            if class_name is None:
                msg = f">>>ERROR: getting constructor but class name is None, {code=}"
                raise ValueError(msg)
            if class_name != name:
                msg = f">>>ERROR: class name {class_name} does not match function name {name}"
                raise ValueError(msg)
            fn = CPPFunction(c_constructor(), class_name, _subelem=nested)
            if context:
                vs = split_function_arguments(context, subelem=True)
                fn.content.extend(vs)
            return fn, find_function_ending(tail)
        case None:
            msg = f">>>ERROR: constructor {code} does not have call braces"
            raise ValueError(msg)


def get_destructor(code: str) -> tuple[None, str | None]:
    match get_context(code, Braces.round):
        case (_, _, tail):
            return None, find_function_ending(tail)
        case None:
            msg = f">>>ERROR: destructor code does not have call braces: {code}"
            raise ValueError(msg)


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
        msg = f">>>ERROR: cannot find context for class {name} in code: {code}"
        raise ValueError(msg)
    item = CPPClass(name)
    _, context, tail = content
    context = get_classmembers_public(context)
    while context:
        members, context = get_item_from_code(context, name, nested=True)
        if isinstance(members, CPPVar | CPPFunction):
            item.content.append(members)
    tail = check_for_semicolon(tail)
    if tail:
        return item, tail
    return item, None


def get_typedef_instance(code: str) -> tuple[None, str | None]:
    first = code.find(";")
    return None, code[first + 1 :].strip()


def get_inline_instance(code: str) -> tuple[None, str | None]:
    _, rest = code.split(None, 1)
    _, tail = get_item_from_code(rest)
    return None, tail


def get_template_instance(code: str) -> tuple[None, str | None]:
    match get_context(code, Braces.angle):
        case (_, _, rest):
            _, tail = get_item_from_code(rest)
            if tail is None:
                return None, None
            return None, check_for_semicolon(tail)
        case None:
            msg = f">>>ERROR: template code does not have angle braces: {code}"
            raise ValueError(msg)


def valid_function_arg(v_type: Ctype) -> bool:
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
    for v in fn.content:
        if not valid_function_arg(v.kind):
            return None
    return fn


def get_item_from_code(
    code: str,
    class_name: str | None = None,
    *,
    nested: bool = False,
) -> tuple[CPPVar | CPPFunction | CPPClass | None, str | None]:
    kind = check_next_type(code, class_name)
    match kind:
        case CPPObject.cls:
            kind, rest = get_class_instance(code)
        case CPPObject.var:
            kind, rest = get_variable_instance(code, nested=nested)
        case CPPObject.func:
            member, rest = get_function_instance(code, nested=nested)
            kind = function_arg_check(member)
        case CPPObject.constructor:
            member, rest = get_constructor(code, class_name, nested=nested)
            kind = function_arg_check(member)
        case CPPObject.destructor:
            kind, rest = get_destructor(code)
        case CPPObject.typedef:
            kind, rest = get_typedef_instance(code)
        case CPPObject.template:
            kind, rest = get_template_instance(code)
        case CPPObject.inline:
            kind, rest = get_inline_instance(code)
        case _:
            print(code)
            raise NotImplementedError
    return kind, rest
