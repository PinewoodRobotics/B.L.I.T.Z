import ctypes
from backend.generated.messages import VALUE
assert VALUE == 'portable-generated-ok'
print(ctypes.CDLL('libcommon.so').common_value())
