import { Matrix, Vector } from "./math-util";

export interface Position2D {
  x: number;
  y: number;
  direction_vector: Matrix<number, 2, 1>;
}

export interface Position3D {
  x: number;
  y: number;
  z: number;
  direction_vector: Vector<number, 3>;
}
