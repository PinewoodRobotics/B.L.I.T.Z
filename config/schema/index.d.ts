import KalmanFilter from "./kalman-filter";

export default interface Config {
  name: string;
  age: number;
  kalmanFilter: KalmanFilter | undefined; // TODO: remove this
}
