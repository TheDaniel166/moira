import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from moira.transits import _find_crossing, _lon, get_reader
from moira.constants import Body

def test_aspect():
    reader = get_reader()
    print("Reader loaded.")

if __name__ == "__main__":
    test_aspect()
