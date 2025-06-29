import type {
  Matrix3x3,
  Matrix4x4,
  Matrix6x6,
  Vector3D,
  Vector4D,
  Vector5D,
  Vector6D,
} from "../../../blitz/generated/thrift/gen-nodejs/common_types";

export type TransformationMatrix3D = Matrix4x4;

function createMatrixProps<T extends Matrix3x3 | Matrix4x4 | Matrix6x6>(
  array: number[][],
  size: number
): T {
  const result: any = {};
  for (let i = 1; i <= size; i++) {
    result[`r${i}`] = VectorUtil.fromArray(array[i - 1]);
  }
  return result as T;
}

export class MatrixUtil {
  static createTransformationMatrix3D(
    rotation: Matrix3x3,
    translation: Vector3D
  ): TransformationMatrix3D {
    return {
      r1: VectorUtil.fromArray<4>([
        rotation.r1.k1,
        rotation.r1.k2,
        rotation.r1.k3,
        0,
      ]) as Vector4D,
      r2: VectorUtil.fromArray<4>([
        rotation.r2.k1,
        rotation.r2.k2,
        rotation.r2.k3,
        0,
      ]) as Vector4D,
      r3: VectorUtil.fromArray<4>([
        rotation.r3.k1,
        rotation.r3.k2,
        rotation.r3.k3,
        0,
      ]) as Vector4D,
      r4: VectorUtil.fromArray<4>([
        translation.k1,
        translation.k2,
        translation.k3,
        1,
      ]) as Vector4D,
    };
  }

  static buildMatrix<R extends number, C extends number>(
    array: number[][]
  ): R extends 3
    ? C extends 3
      ? Matrix3x3
      : null
    : R extends 4
    ? C extends 4
      ? Matrix4x4
      : null
    : R extends 6
    ? C extends 6
      ? Matrix6x6
      : null
    : null {
    if (!array || array.length === 0 || !array[0]) {
      return null as any;
    }

    const rows = array.length;
    const cols = array[0].length;

    if (rows === 3 && cols === 3) {
      return {
        r1: VectorUtil.fromArray<3>(array[0] as [number, number, number]),
        r2: VectorUtil.fromArray<3>(array[1] as [number, number, number]),
        r3: VectorUtil.fromArray<3>(array[2] as [number, number, number]),
      } as any;
    }

    if (rows === 4 && cols === 4) {
      return createMatrixProps<Matrix4x4>(array, 4) as any;
    }

    if (rows === 6 && cols === 6) {
      return createMatrixProps<Matrix6x6>(array, 6) as any;
    }

    return null as any;
  }
}

export class VectorUtil {
  static fromArray<L extends number>(
    array: L extends 3
      ? [number, number, number]
      : L extends 4
      ? [number, number, number, number]
      : L extends 5
      ? [number, number, number, number, number]
      : L extends 6
      ? [number, number, number, number, number, number]
      : number[]
  ): L extends 3
    ? Vector3D
    : L extends 4
    ? Vector4D
    : L extends 5
    ? Vector5D
    : L extends 6
    ? Vector6D
    : null {
    if (!array || array.length === 0) {
      return null as any;
    }

    if (array.length === 3) {
      return {
        k1: array[0],
        k2: array[1],
        k3: array[2],
      } as any;
    }

    if (array.length === 4) {
      return {
        k1: array[0],
        k2: array[1],
        k3: array[2],
        k4: array[3],
      } as any;
    }

    if (array.length === 5) {
      return {
        k1: array[0],
        k2: array[1],
        k3: array[2],
        k4: array[3],
        k5: array[4],
      } as any;
    }

    if (array.length === 6) {
      return {
        k1: array[0],
        k2: array[1],
        k3: array[2],
        k4: array[3],
        k5: array[4],
        k6: array[5],
      } as any;
    }

    return null as any;
  }
}
