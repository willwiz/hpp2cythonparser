import sys

from .api import create_cython_header

if __name__ == "__main__":
    create_cython_header(sys.argv[1])
