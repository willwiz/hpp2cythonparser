from __future__ import annotations

__all__ = [
    "CPPFunctionTypes",
    "CPPObject",
    "Ctype",
    "CtypeExtended",
]
import abc
import enum


class CPPObject(enum.Enum):
    var = 0
    func = 1
    cls = 2
    template = 3
    inline = 4
    typedef = 5
    constructor = 6
    destructor = 7
    unknown = 10


class CPPFunctionTypes(enum.StrEnum):
    void = "void"
    int = "int"
    double = "double"
    constructor = ""
    destructor = "~"


class CtypeExtended(abc.ABC):
    @abc.abstractmethod
    def __str__(self) -> str:
        """Convert the C type to a string representation."""


class Ctype(CtypeExtended):
    @abc.abstractmethod
    def __str__(self) -> str:
        """Convert the C type to a string representation."""
