import {
  Matrix3x3,
  Matrix4x4,
  Vector3D,
} from "../../generated_schema/common_types";

class Matrix3 extends Matrix3x3 {
  constructor(vec1: Vector3D, vec2: Vector3D, vec3: Vector3D) {
    super({
      m00: vec1.x,
      m01: vec1.y,
      m02: vec1.z,
      m10: vec2.x,
      m11: vec2.y,
      m12: vec2.z,
      m20: vec3.x,
      m21: vec3.y,
      m22: vec3.z,
    });
  }
}

class TransformationMatrix3 extends Matrix4x4 {
  constructor(rotation: Matrix3x3, translation: Vector3D) {
    super({
      m00: rotation.m00,
      m01: rotation.m01,
      m02: rotation.m02,
      m03: 0,
      m10: rotation.m10,
      m11: rotation.m11,
      m12: rotation.m12,
      m13: 0,
      m20: rotation.m20,
      m21: rotation.m21,
      m22: rotation.m22,
      m23: 0,
      m30: translation.x,
      m31: translation.y,
      m32: translation.z,
      m33: 1,
    });
  }
}
