import type {
  GenericMatrix,
  GenericVector,
} from "generated/thrift/gen-nodejs/common_types";

export function fromQuaternionNoRoll_ZYX(q: number[]): GenericMatrix {
  let [w, x, y, z] = q;
  const n = Math.sqrt(w * w + x * x + y * y + z * z) || 1;
  w /= n;
  x /= n;
  y /= n;
  z /= n;

  const siny_cosp = 2 * (w * z + x * y);
  const cosy_cosp = 1 - 2 * (y * y + z * z);
  const yaw = Math.atan2(siny_cosp, cosy_cosp);

  const sinp = 2 * (w * y - z * x);
  const pitch =
    Math.abs(sinp) >= 1
      ? (sinp >= 0 ? 1 : -1) * (Math.PI / 2)
      : Math.asin(sinp);

  const cy = Math.cos(yaw),
    sy = Math.sin(yaw);
  const cp = Math.cos(pitch),
    sp = Math.sin(pitch);

  const r11 = cy * cp,
    r12 = -sy,
    r13 = cy * sp;
  const r21 = sy * cp,
    r22 = cy,
    r23 = sy * sp;
  const r31 = -sp,
    r32 = 0,
    r33 = cp;

  return MatrixUtil.buildMatrix([
    [r11, r12, r13],
    [r21, r22, r23],
    [r31, r32, r33],
  ]);
}
export class MatrixUtil {
  static createTransformationMatrix3D(
    rotation: GenericMatrix,
    translation: GenericVector
  ): GenericMatrix {
    return {
      values: [
        [
          rotation.values[0][0],
          rotation.values[1][0],
          rotation.values[2][0],
          translation.values[0],
        ],
        [
          rotation.values[0][1],
          rotation.values[1][1],
          rotation.values[2][1],
          translation.values[1],
        ],
        [
          rotation.values[0][2],
          rotation.values[1][2],
          rotation.values[2][2],
          translation.values[2],
        ],
        [0, 0, 0, 1],
      ],
      rows: 4,
      cols: 4,
    };
  }

  /**
   *
   * @param array [[1, 2, 3], [4, 5, 6], [7, 8, 9]] --> 3x3 matrix with [1, 2, 3] as the first row
   * @returns
   */
  static buildMatrix(array: number[][]): GenericMatrix {
    return {
      values: array,
      rows: array.length,
      cols: array[0].length,
    } as GenericMatrix;
  }

  static buildMatrixFromDiagonal(diagonal: number[]): GenericMatrix {
    const size = diagonal.length;
    const values = Array.from({ length: size }, (_, i) =>
      Array.from({ length: size }, (_, j) => (i === j ? diagonal[i] : 0))
    );
    return {
      values,
      rows: size,
      cols: size,
    } as GenericMatrix;
  }
}

export class VectorUtil {
  /**
   *
   * @param array [1, 2, 3] --> x = 1, y = 2, z = 3
   * @returns
   */
  static fromArray(array: number[]): GenericVector {
    return {
      values: array,
      size: array.length,
    } as GenericVector;
  }
}
