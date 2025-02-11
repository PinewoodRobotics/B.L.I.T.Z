import type { Matrix, Vector } from "../../schema/type-util/math-util";

/**
 *
 * @param type
 * @param size
 * @returns
 */
export function buildIdentityMatrix<T, N extends number>(
  type: T,
  size: N
): Matrix<T, N, N> {
  return Array.from({ length: size }, (_, i) =>
    Array.from({ length: size }, (_, j) => (i === j ? type : 0))
  ) as Matrix<T, N, N>;
}

export function buildVector<T, N extends number>(...values: T[]): Vector<T, N> {
  if (values.length === 0) {
    throw new Error("Vector must contain at least one value");
  }

  return values as Vector<T, N>;
}

export function buildMatrix<T, N extends number, M extends number>(
  ...values: T[]
): Matrix<T, N, M> {
  if (values.length === 0) {
    throw new Error("Matrix must contain at least one value");
  }

  return values as Matrix<T, N, M>;
}

export function buildMatrixFromArray<T, N extends number, M extends number>(
  arrays: T[][]
): Matrix<T, N, M> {
  if (arrays.length === 0 || arrays[0].length === 0) {
    throw new Error("Matrix must contain at least one row and column");
  }

  const width = arrays[0].length;
  if (!arrays.every((row) => row.length === width)) {
    throw new Error("All rows must have the same length");
  }

  return arrays as Matrix<T, N, M>;
}
