import os
import enum
from typing import Literal


class Braces(enum.Enum):
    round = ("(", ")", 1)
    square = ("[", "]", 1)
    curly = ("{", "}", 1)
    comment = ("/*", "*/", 2)
    angle = ("<", ">", 1)


def check_for_semicolon(code: str) -> str:
    if code.startswith(";"):
        return code[1:].strip()
    return code.strip()


def get_brace_count(
    data: str,
    init_count: int = 1,
    opening: Literal["(", "[", "{", "<", "/*"] = "{",
    closing: Literal[")", "]", "}", ">", "*/"] = "}",
) -> int | None:
    count = init_count
    for i, c in enumerate(data):
        if c == opening:
            count = count + 1
        elif c == closing:
            count = count - 1
        if count == 0:
            return i
    return None


def get_context(data: str, brace: Braces) -> tuple[str, str, str] | None:
    left, right, n = brace.value
    start = data.find(left)
    if start == -1:
        return None
    end = get_brace_count(data[start + 1 :], opening=left, closing=right)
    if end is None:
        raise ValueError(f"End of context {right} not found in {data=}")
    return (
        data[:start].strip(),
        data[start + n : start + n + end].strip(),
        data[start + n + end + n :].strip(),
    )


def read_cppfile(name: str) -> list[str]:
    if not os.path.isfile(name):
        raise ValueError(f"Cannot find file {name}")
    with open(name, "r") as fin:
        file = fin.read().split("\n")
    if file[0].startswith("#pragma"):
        file = file[1:]
    file = [line for line in file if not (line.startswith("#define"))]
    file = [line.split("//")[0].strip() for line in file]
    file = [line for line in file if line]
    return file


def filterline(code: list[str], word: str) -> list[str]:
    return [line for line in code if not line.startswith(word)]


def remove_comment(file: list[str]) -> str:
    raw = " ".join(file)
    while True:
        match get_context(raw, Braces.comment):
            case str(head), str(), str(tail):
                raw = " ".join([head, tail])
            case None:
                break
    return raw
