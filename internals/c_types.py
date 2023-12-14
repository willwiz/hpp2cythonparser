import dataclasses as dc
from typing import Final, Literal, Self, TypeAlias


@dc.dataclass(slots=True)
class c_void:
    val: Final[str] = "void"

    def to_str(self):
        return self.val


@dc.dataclass(slots=True)
class c_int:
    val: Final[str] = "int"

    def to_str(self):
        return self.val


@dc.dataclass(slots=True)
class c_double:
    val: Final[str] = "double"

    def to_str(self):
        return self.val


@dc.dataclass(slots=True)
class c_generic:
    val: Final[str]

    def to_str(self):
        return self.val


@dc.dataclass(slots=True)
class c_generic_t:
    val: Final[str]
    args: Final[list[str]]

    def to_str(self):
        return f"{self.val}[{', '.join(self.args)}]"


@dc.dataclass(slots=True)
class c_constructor:
    val: Final[str] = ""

    def to_str(self):
        return self.val


@dc.dataclass(slots=True)
class c_destructor:
    val: Final[str] = "~"

    def to_str(self):
        return self.val


@dc.dataclass(slots=True)
class c_ptr:
    kind: c_void | c_int | c_double | c_generic | c_generic_t | Self = dc.field(
        default_factory=c_void
    )
    char: Literal["[]", "*"] = "*"

    def to_str(self):
        return f"{self.kind.to_str()}{self.char}"


c_types: TypeAlias = c_void | c_int | c_double | c_generic | c_generic_t | c_ptr

c_types_extended: TypeAlias = (
    c_void | c_int | c_double | c_generic | c_generic_t | c_ptr | c_constructor
)
