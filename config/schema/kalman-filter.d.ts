import { Matrix } from "./type-util/math-util";

export default interface KalmanFilter {
  state: Matrix<number, 3, 1>;
  covariance: Matrix<number, 3, 3>;
  transitionMatrix: Matrix<number, 3, 3>;
  controlMatrix: Matrix<number, 3, 1>;
}
