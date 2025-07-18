from __future__ import annotations

__all__ = [
    "function_arg_check",
    "get_class_instance",
    "get_classmembers_public",
    "get_constructor",
    "get_destructor",
    "get_function_instance",
    "get_inline_instance",
    "get_item_from_code",
    "get_template_instance",
    "get_typedef_instance",
    "get_variable_instance",
    "parse_include",
    "split_function_arguments",
    "valid_function_arg",
]
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from hpp2cythonparser._c_types import (
    c_constructor,
    c_double,
    c_generic,
    c_generic_t,
    c_int,
    c_ptr,
    c_struct,
    c_void,
)
from hpp2cythonparser.struct import CPPClass, CPPFunction, CPPVar
from hpp2cythonparser.trait import CPPObject, Ctype

from .ctype_parsing import check_next_type, get_variable_type
from .tools import Braces, check_for_semicolon, get_context

if TYPE_CHECKING:
    from pytools.logging.trait import ILogger

_INCLUDE_SIZE = 2


def parse_include(code: str, exclude: str, folder: Path | str) -> str | None:
    splitted_code = [s.strip() for s in code.strip().split()]
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


def get_variable_instance(code: str, *, nested: bool = False) -> tuple[CPPVar | None, str | None]:
    kind, rest = get_variable_type(code)
    vs, rest = [s.strip() for s in rest.split(";", 1)]
    rest = check_for_semicolon(rest)
    vs = [v.strip() for v in vs.split(",")]
    array_depth = [v.count("]") for v in vs]
    if array_depth.count(array_depth[0]) != len(array_depth):
        msg = f">>>ERROR: vars do not have the same array depth, {vs=}"
        raise ValueError(msg)
    if array_depth[0] > 0:
        kind = c_ptr(kind, f"[{','.join([':' for _ in range(array_depth[0])])}]")
    v_list = [v.split("=")[0] for v in vs]
    v_list = [v.split("[")[0] for v in v_list]
    match kind:
        case c_generic_t():
            var = None
        case c_generic():
            var = None
        case c_struct():
            var = None
        case c_ptr(c_generic_t() | c_generic() | c_struct()):
            var = None
        case _:
            var = CPPVar(kind, ", ".join(v_list), nested)
    return var, rest if rest else None


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


def get_class_instance(code: str, log: ILogger) -> tuple[CPPClass, str | None]:
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
        members, context = get_item_from_code(context, log, name, nested=True)
        if isinstance(members, CPPVar | CPPFunction):
            item.content.append(members)
    tail = check_for_semicolon(tail)
    if tail:
        return item, tail
    return item, None


def get_typedef_instance(code: str) -> tuple[None, str | None]:
    first = code.find(";")
    return None, code[first + 1 :].strip()


def get_inline_instance(code: str, log: ILogger) -> tuple[None, str | None]:
    _, rest = code.split(None, 1)
    _, tail = get_item_from_code(rest, log)
    return None, tail


def get_template_instance(code: str, log: ILogger) -> tuple[None, str | None]:
    match get_context(code, Braces.angle):
        case (_, _, rest):
            _, tail = get_item_from_code(rest, log)
            if tail is None:
                return None, None
            return None, check_for_semicolon(tail)
        case None:
            msg = f">>>ERROR: template code does not have angle braces: {code}"
            raise ValueError(msg)


def valid_function_arg(v_type: Ctype, log: ILogger) -> bool:
    match v_type:
        case c_ptr():
            valid_function_arg(v_type.kind, log)
        case c_void() | c_int() | c_double() | c_generic():
            pass
        case c_struct():
            log.warn(">>>>WARNING: struct type in function args, ignored")
            return False
        case c_generic_t():
            log.warn(">>>>WARNING: generic type in function args, ignored")
            return False
        case _:
            log.warn(f">>>>WARNING: inadmissible type {v_type}, ignored")
            return False
    return True


def function_arg_check(fn: CPPFunction, log: ILogger) -> CPPFunction | None:
    for v in fn.content:
        if not valid_function_arg(v.kind, log):
            return None
    return fn


def get_item_from_code(
    code: str,
    log: ILogger,
    class_name: str | None = None,
    *,
    nested: bool = False,
) -> tuple[CPPVar | CPPFunction | CPPClass | None, str | None]:
    kind = check_next_type(code, class_name)
    match kind:
        case CPPObject.cls:
            kind, rest = get_class_instance(code, log)
        case CPPObject.var:
            kind, rest = get_variable_instance(code, nested=nested)
        case CPPObject.func:
            member, rest = get_function_instance(code, nested=nested)
            kind = function_arg_check(member, log)
        case CPPObject.constructor:
            member, rest = get_constructor(code, class_name, nested=nested)
            kind = function_arg_check(member, log)
        case CPPObject.destructor:
            kind, rest = get_destructor(code)
        case CPPObject.typedef:
            kind, rest = get_typedef_instance(code)
        case CPPObject.template:
            kind, rest = get_template_instance(code, log)
        case CPPObject.inline:
            kind, rest = get_inline_instance(code, log)
        case _:
            log.error(code)
            raise NotImplementedError
    return kind, rest
