namespace py config.common

struct Vector2D {
    1: required double k1,
    2: required double k2,
}

struct Vector3D {
    1: required double k1,
    2: required double k2,
    3: required double k3,
}

struct Vector4D {
    1: required double k1,
    2: required double k2,
    3: required double k3,
    4: required double k4,
}

struct Vector5D {
    1: required double k1,
    2: required double k2,
    3: required double k3,
    4: required double k4,
    5: required double k5,
}

struct Vector6D {
    1: required double k1,
    2: required double k2,
    3: required double k3,
    4: required double k4,
    5: required double k5,
    6: required double k6,
}

struct Point3 {
    1: required Vector3D position,
    2: required Matrix3x3 rotation,
}

struct Matrix3x3 {
    1: required Vector3D r1,
    2: required Vector3D r2,
    3: required Vector3D r3,
}

struct Matrix4x4 {
    1: required Vector4D r1,
    2: required Vector4D r2,
    3: required Vector4D r3,
    4: required Vector4D r4,
}

struct Matrix5x5 {
    1: required Vector5D r1,
    2: required Vector5D r2,
    3: required Vector5D r3,
    4: required Vector5D r4,
    5: required Vector5D r5,
}

struct Matrix6x6 {
    1: required Vector6D r1,
    2: required Vector6D r2,
    3: required Vector6D r3,
    4: required Vector6D r4,
    5: required Vector6D r5,
    6: required Vector6D r6,
}

struct UnitConversion {
    1: required double non_unit_to_unit,
    2: required double unit_to_non_unit,
}

struct MapData {
    1: required list<bool> map_data,
    2: required i32 map_size_x,
    3: required i32 map_size_y,
}