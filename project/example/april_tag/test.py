
import numpy as np

a = np.column_stack((
    np.array([0, -1, 0]),
    np.array([0, 0, -1]),
    np.array([1, 0, 0])
))

v = a[:3, 1]
print(v)



