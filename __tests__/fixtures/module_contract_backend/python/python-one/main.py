from common.values import expected_value
import ctypes
import os
from pathlib import Path
assert ctypes.CDLL('libcommon.so').common_value() == expected_value()
print(ctypes.CDLL('libcommon.so').common_value(), Path('assets/value.txt').read_text().strip(), Path(os.environ['BLITZ_RESOURCE_DIR'], 'assets/value.txt').read_text().strip())
