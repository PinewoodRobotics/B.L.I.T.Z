from common.values import expected_value
from backend.generated.messages import VALUE
from backend.generated import shared_stub
import ctypes
import os
from pathlib import Path
assert VALUE == 'portable-generated-ok'
assert shared_stub.VALUE == 42
assert Path(os.environ['BLITZ_GENERATED_DIR'], 'messages/schema.txt').read_text().strip() == 'portable-schema'
assert ctypes.CDLL('libcommon.so').common_value() == expected_value()
print(ctypes.CDLL('libcommon.so').common_value(), Path('assets/value.txt').read_text().strip(), Path(os.environ['BLITZ_RESOURCE_DIR'], 'assets/value.txt').read_text().strip())
