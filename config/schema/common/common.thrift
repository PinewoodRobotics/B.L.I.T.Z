namespace py thrift.common

struct Vector3D {
    1: required double x,
    2: required double y,
    3: required double z,
}

struct Vector2D {
    1: required double x,
    2: required double y,
}

struct Vector5D {
    1: required double k1,
    2: required double k2,
    3: required double p1,
    4: required double p2,
    5: required double k3,
}

struct Vector6D {
    1: required double x,
    2: required double y,
    3: required double z,
    4: required double vx,
    5: required double vy,
    6: required double vz,
}

struct Point3 {
    1: required Vector3D point,
    2: required Matrix3x3 rotation,
}

struct Matrix3x3 {
    1: required double m00,
    2: required double m01,
    3: required double m02,
    4: required double m10,
    5: required double m11,
    6: required double m12,
    7: required double m20,
    8: required double m21,
    9: required double m22,
}

struct Matrix4x4 {
    1: required double m00,
    2: required double m01,
    3: required double m02,
    4: required double m03,
    5: required double m10,
    6: required double m11,
    7: required double m12,
    8: required double m13,
    9: required double m20,
    10: required double m21,
    11: required double m22,
    12: required double m23,
    13: required double m30,
    14: required double m31,
    15: required double m32,
    16: required double m33,
}

struct Matrix6x6 {
    1: required double m00,
    2: required double m01,
    3: required double m02,
    4: required double m03,
    5: required double m04,
    6: required double m05,
    7: required double m10,
    8: required double m11,
    9: required double m12,
    10: required double m13,
    11: required double m14,
    12: required double m15,
    13: required double m20,
    14: required double m21,
    15: required double m22,
    16: required double m23,
    17: required double m24,
    18: required double m25,
    19: required double m30,
    20: required double m31,
    21: required double m32,
    22: required double m33,
    23: required double m34,
    24: required double m35,
    25: required double m40,
    26: required double m41,
    27: required double m42,
    28: required double m43,
    29: required double m44,
    30: required double m45,
    31: required double m50,
    32: required double m51,
    33: required double m52,
    34: required double m53,
    35: required double m54,
    36: required double m55,
}