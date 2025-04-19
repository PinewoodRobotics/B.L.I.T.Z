import type {
  Matrix3x3,
  Matrix4x4,
  Matrix6x6,
  Vector3D,
  Vector5D,
  Vector6D,
} from "../../generated_schema/common_types";

export type TransformationMatrix3D = Matrix4x4;

function createMatrixProps<T extends Matrix3x3 | Matrix4x4 | Matrix6x6>(
  array: number[][],
  size: number
): T {
  const props = {} as T;
  for (let i = 0; i < size; i++) {
    for (let j = 0; j < size; j++) {
      (props as any)[`m${i}${j}`] = array[i][j];
    }
  }
  return props;
}

export class MatrixUtil {
  static createTransformationMatrix3D(
    rotation: Matrix3x3,
    translation: Vector3D
  ): TransformationMatrix3D {
    return createMatrixProps<Matrix4x4>(
      [
        [rotation.m00, rotation.m01, rotation.m02, 0],
        [rotation.m10, rotation.m11, rotation.m12, 0],
        [rotation.m20, rotation.m21, rotation.m22, 0],
        [translation.x, translation.y, translation.z, 1],
      ],
      4
    );
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
    const rows = array.length;
    const cols = array[0].length;

    if (rows === 3 && cols === 3) {
      return createMatrixProps<Matrix3x3>(array, 3) as any;
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
      : L extends 5
      ? [number, number, number, number, number]
      : L extends 6
      ? [number, number, number, number, number, number]
      : number[]
  ): L extends 3
    ? Vector3D
    : L extends 5
    ? Vector5D
    : L extends 6
    ? Vector6D
    : null {
    if (array.length === 3) {
      return {
        x: array[0],
        y: array[1],
        z: array[2],
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
