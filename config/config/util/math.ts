import { Matrix } from "../../schema/type-util/math-util";

export function buildIdentityMatrix<T, N extends number>(
  type: T,
  size: N
): Matrix<T, N, N> {
  return Array.from({ length: size }, (_, i) =>
    Array.from({ length: size }, (_, j) => (i === j ? type : 0))
  ) as Matrix<T, N, N>;
}
