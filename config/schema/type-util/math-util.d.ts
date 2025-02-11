/**
 * Represents a tuple of a specified length.
 *
 * @param T The type of each element in the tuple.
 * @param N The length of the tuple.
 * @param R The current tuple being constructed.
 *
 * This type recursively constructs a tuple of length N by adding elements of type T.
 * When the length of R is equal to N, it returns R. Otherwise, it adds another element of type T to R.
 */
export type Tuple<
  T,
  N extends number,
  R extends T[] = []
> = R["length"] extends N ? R : Tuple<T, N, [...R, T]>;

/**
 * Represents a matrix of a specified width and height.
 *
 * @param T The type of each element in the matrix.
 * @param Width The width of the matrix.
 * @param Height The height of the matrix.
 *
 * This type uses Tuple to construct a matrix. It first constructs a tuple of length Width to represent a row,
 * then constructs a tuple of length Height to represent the matrix, where each element is a row tuple.
 */
export type Matrix<T, Width extends number, Height extends number> = Tuple<
  Tuple<T, Width>,
  Height
>;

/**
 * Represents a vector of a specified length.
 *
 * @param T The type of each element in the vector.
 * @param Length The length of the vector.
 *
 * This type uses Tuple to construct a vector. It first constructs a tuple of length Length to represent the vector,
 * where each element is of type T.
 */
export type Vector<T, Length extends number> = Tuple<T, Length>;
