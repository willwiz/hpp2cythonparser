# ruff: noqa: N801
__all__ = [
    "Ctype",
    "CtypeExtended",
    "c_constructor",
    "c_destructor",
    "c_double",
    "c_generic",
    "c_generic_t",
    "c_int",
    "c_ptr",
    "c_struct",
    "c_void",
]
import abc
import dataclasses as dc
from typing import Final


class CtypeExtended(abc.ABC):
    @abc.abstractmethod
    def __str__(self) -> str:
        """Convert the C type to a string representation."""


class Ctype(CtypeExtended):
    @abc.abstractmethod
    def __str__(self) -> str:
        """Convert the C type to a string representation."""


@dc.dataclass(slots=True)
class c_void(Ctype):
    val: Final[str] = "void"

    def __str__(self) -> str:
        return self.val


@dc.dataclass(slots=True)
class c_int(Ctype):
    val: Final[str] = "int"

    def __str__(self) -> str:
        return self.val


@dc.dataclass(slots=True)
class c_double(Ctype):
    val: Final[str] = "double"

    def __str__(self) -> str:
        return self.val


@dc.dataclass(slots=True)
class c_struct(Ctype):
    val: Final[str] = "struct"

    def __str__(self) -> str:
        return self.val


@dc.dataclass(slots=True)
class c_generic(Ctype):
    val: Final[str]

    def __str__(self) -> str:
        return self.val


@dc.dataclass(slots=True)
class c_generic_t(Ctype):
    val: Final[str]
    args: Final[list[str]]

    def __str__(self) -> str:
        return f"{self.val}[{', '.join(self.args)}]"


@dc.dataclass(slots=True)
class c_ptr(Ctype):
    kind: Ctype = dc.field(
        default_factory=c_void,
    )
    # char: Literal["[]", "*", "[:,:]", "[:,:,:]"] = "*"
    char: str = "*"

    def __str__(self) -> str:
        return f"{self.kind}{self.char}"


@dc.dataclass(slots=True)
class c_constructor(CtypeExtended):
    val: Final[str] = ""

    def __str__(self) -> str:
        return self.val


@dc.dataclass(slots=True)
class c_destructor(CtypeExtended):
    val: Final[str] = "~"

    def __str__(self) -> str:
        return self.val
