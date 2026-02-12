import sys
from pathlib import Path


def version():
    _version = Path("tesp_support/_version.py").read_text()
    _version = _version.split("\"")[1]
    print(_version)

def tesp_support():
    if sys.argv.__len__() == 2:
        if sys.argv[1] == "-v" or sys.argv[1] == "--version":
            version()
