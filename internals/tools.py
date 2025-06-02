from __future__ import annotations

import enum
from pathlib import Path
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
        msg = f">>>ERROR: end of context {left} not found in {data=}"
        raise ValueError(msg)
    return (
        data[:start].strip(),
        data[start + n : start + n + end].strip(),
        data[start + n + end + n :].strip(),
    )


def read_cppfile(name: Path | str) -> list[str]:
    name = Path(name)
    if not name.is_file():
        msg = f">>>ERROR: file {name} does not exist"
        raise ValueError(msg)
    with name.open("r") as fin:
        file = fin.read().split("\n")
    if file[0].startswith("#pragma"):
        file = file[1:]
    file = [line for line in file if not (line.startswith("#define"))]
    file = [line.split("//")[0].strip() for line in file]
    return [line for line in file if line]


def filterline(code: list[str], word: str) -> list[str]:
    return [line for line in code if not line.startswith(word)]


def remove_comment(file: list[str]) -> str:
    raw = " ".join(file)
    while True:
        match get_context(raw, Braces.comment):
            case str(head), str(), str(tail):
                raw = f"{head} {tail}"
            case None:
                break
    return raw
