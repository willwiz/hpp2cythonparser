from __future__ import annotations

__all__ = ["CPPClass", "CPPFunction", "CPPVar"]
import dataclasses as dc
import textwrap
from typing import TYPE_CHECKING

from ._c_types import c_constructor

if TYPE_CHECKING:
    from .trait import Ctype, CtypeExtended


@dc.dataclass(slots=True)
class CPPVar:
    kind: Ctype
    name: str
    _subelem: bool = False

    def __str__(self) -> str:
        if self._subelem:
            return f"  {self.kind} {self.name}"
        return f"  cdef {self.kind} {self.name}"


@dc.dataclass(slots=True)
class CPPFunction:
    kind: CtypeExtended
    name: str
    content: list[CPPVar] = dc.field(default_factory=list[CPPVar])
    _subelem: bool = False

    def __str__(self) -> str:
        wrapper = textwrap.TextWrapper(
            width=80,
            initial_indent="  ",
            subsequent_indent="    ",
            break_long_words=False,
        )
        hacky = [str(s).strip().replace(" ", "$") for s in self.content]
        string = f"{self.kind} {self.name}({', '.join(hacky)})".strip()
        if not self._subelem:
            string = "cdef " + string
        if isinstance(self.kind, c_constructor):
            string = string + "$except$+"
        return "\n".join(wrapper.wrap(text=string)).replace("$", " ")


@dc.dataclass(slots=True)
class CPPClass:
    name: str
    content: list[CPPFunction | CPPVar] = dc.field(default_factory=list[CPPFunction | CPPVar])

    def __str__(self) -> str:
        head = f"  cdef cppclass {self.name}:"
        string = ""
        if self.content:
            for el in self.content:
                string = string + "\n" + str(el)
        else:
            string = string + "\n  pass"
        return head + string.replace("\n", "\n  ")
