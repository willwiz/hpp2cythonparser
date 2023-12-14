import enum
import dataclasses as dc
import textwrap
from tools import get_context, Braces
from c_types import (
    c_constructor,
    c_types,
    c_types_extended,
    c_void,
    c_int,
    c_double,
    c_generic,
    c_generic_t,
    c_ptr,
)


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


@dc.dataclass(slots=True)
class CPPVar:
    kind: c_types
    name: str

    def to_string(self, subelem=False):
        if subelem:
            return f"  {self.kind.to_str()} {self.name}"
        else:
            return f"  cdef {self.kind.to_str()} {self.name}"


@dc.dataclass(slots=True)
class CPPFunction:
    kind: c_types_extended
    name: str
    content: list[CPPVar] = dc.field(default_factory=list)

    def to_string(self, subelem=False):
        wrapper = textwrap.TextWrapper(
            width=80,
            initial_indent="  ",
            subsequent_indent="    ",
            break_long_words=False,
        )
        hacky = [
            s.to_string(subelem=True).strip().replace(" ", "$") for s in self.content
        ]
        string = f"{self.kind.to_str()} {self.name}({', '.join(hacky)})".strip()
        if not subelem:
            string = "cdef " + string
        if isinstance(self.kind, c_constructor):
            string = string + " except +"
        return "\n".join(wrapper.wrap(text=string)).replace("$", " ")


@dc.dataclass(slots=True)
class CPPClass:
    name: str
    content: list[CPPFunction | CPPVar] = dc.field(default_factory=list)

    def to_string(self):
        head = f"  cdef cppclass {self.name}:"
        string = ""
        if self.content:
            for el in self.content:
                string = string + "\n" + el.to_string(subelem=True)
        else:
            string = string + "\n  pass"
        return head + string.replace("\n", "\n  ")


def check_next_type(code: str, class_name: str | None = None) -> CPPObject:
    if class_name:
        if code.startswith(class_name):
            return CPPObject.constructor
        elif code.startswith(f"~{class_name}"):
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
    elif func_brace == -1:
        return CPPObject.var
    elif colon_stop < func_brace:
        return CPPObject.var
    else:
        return CPPObject.func


def get_variable_type(raw_code: str) -> tuple[c_types, str]:
    code = raw_code
    if code.startswith("extern"):
        code = code[6:].strip()
    if code.startswith("const"):
        code = code[5:].strip()
    head, tail = code.split(None, 1)
    if head.startswith("void"):
        base_type = c_void()
        head = head[4:]
    elif head.startswith("int"):
        base_type = c_int()
        head = head[3:]
    elif head.startswith("double"):
        base_type = c_double()
        head = head[6:]
    elif "<" in head:
        match get_context(head, Braces.angle):
            case (kind, vars, extras):
                base_type = c_generic_t(kind, [v.strip() for v in vars.split(",")])
            case None:
                raise ValueError(
                    f"template variable {head} does not have closing brace"
                )
        while extras.startswith("*"):
            base_type = c_ptr(base_type)
            extras = extras[1:].strip()
        head = extras
    else:
        extras = head.split("*")
        match extras[0]:
            case "void":
                base_type = c_void()
            case "int":
                base_type = c_int()
            case "double":
                base_type = c_double()
            case s:
                base_type = c_generic(s)
        for _ in range(len(extras) - 1):
            base_type = c_ptr(base_type)
    while head.startswith("*"):
        base_type = c_ptr(base_type)
        head = head[1:].strip()
    return base_type, tail
