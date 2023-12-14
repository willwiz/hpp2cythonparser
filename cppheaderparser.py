import os
from glob import glob
from contextlib import contextmanager
from hpp2cythonparser.hpp_parser import create_cython_header


@contextmanager
def cwd(path):
    oldpwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)


_CPP_HOME: str = os.sep.join(["src", "cpp"])
_CYTHON_HOME: str = os.sep.join(["src", "cython", "headers"])


def main(cpp_home: str | None = None, cython_home: str | None = None):
    with cwd(os.path.dirname(__file__)):
        files = glob("src/cpp/*/*.hpp")
        for fin in files:
            create_cython_header(fin, cpp_home=cpp_home, cython_home=cython_home)
        files = glob("src/cpp/*.hpp")
        for fin in files:
            create_cython_header(fin)


if __name__ == "__main__":
    main(_CPP_HOME, _CYTHON_HOME)
