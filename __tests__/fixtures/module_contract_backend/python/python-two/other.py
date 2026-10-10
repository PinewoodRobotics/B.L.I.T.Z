import ctypes
print(ctypes.CDLL('libcommon.so').common_value())
