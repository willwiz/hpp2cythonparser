# ruff: noqa: PLR0911
from __future__ import annotations

__all__ = [
    "check_next_type",
    "cstrip_prefix",
    "get_variable_type",
]

from typing import TYPE_CHECKING, Literal

from hpp2cythonparser._c_types import (
    c_double,
    c_generic,
    c_generic_t,
    c_int,
    c_ptr,
    c_struct,
    c_void,
)
from hpp2cythonparser.trait import CPPObject, Ctype

from .tools import Braces, get_context

if TYPE_CHECKING:
    from collections.abc import Sequence


def check_next_type(code: str, class_name: str | None = None) -> CPPObject:
    if class_name:
        if code.startswith(class_name):
            return CPPObject.constructor
        if code.startswith(f"~{class_name}"):
            return CPPObject.destructor
    if code.startswith("template"):
        return CPPObject.template
    if code.startswith("inline"):
        return CPPObject.inline
    if code.startswith("typedef"):
        return CPPObject.typedef
    if code.startswith("class"):
        return CPPObject.cls
    colon_stop = code.find(";")
    func_brace = code.find("(")
    if colon_stop == -1:
        return CPPObject.func
    if func_brace == -1 or colon_stop < func_brace:
        return CPPObject.var
    return CPPObject.func


def cstrip_prefix(
    code: str,
    *,
    prefix: Sequence[Literal["extern", "const"]] = ("extern", "const"),
) -> str:
    """Strip the prefix from the code."""
    for p in prefix:
        if code.startswith(p):
            code = code[len(p) :].strip()
    return code


def c_generic_split(code: str) -> tuple[Ctype, str]:
    match get_context(code, Braces.angle):
        case (kind, vars, extras):
            base_type = c_generic_t(kind, [v.strip() for v in vars.split(",")])
        case None:
            msg = f"template variable {code} does not have closing angle brace"
            raise ValueError(msg)
    while extras.startswith("*"):
        base_type = c_ptr(base_type)
        extras = extras[1:].strip()
    return base_type, extras


def c_unkown_split(code: str) -> tuple[Ctype, str]:
    extras = code.split("*")
    match extras[0]:
        case "void":
            base_type = c_void()
        case "int":
            base_type = c_int()
        case "double":
            base_type = c_double()
        case "struct":
            base_type = c_struct()
        case s:
            base_type = c_generic(s)
    for _ in range(len(extras) - 1):
        base_type = c_ptr(base_type)
    return base_type, code


def get_variable_type(raw_code: str) -> tuple[Ctype, str]:
    code = cstrip_prefix(raw_code)
    head, tail = code.split(None, 1)
    if head.startswith("void"):
        base_type, head = c_void(), head[4:]
    elif head.startswith("int"):
        base_type, head = c_int(), head[3:]
    elif head.startswith("double"):
        base_type, head = c_double(), head[6:]
    elif "<" in head:
        base_type, head = c_generic_split(head)
    else:
        base_type, head = c_unkown_split(head)
    while head.startswith("*"):
        base_type = c_ptr(base_type)
        head = head[1:].strip()
    return base_type, tail
