import { MatrixUtil, VectorUtil } from "../../util/math";
import { MapUtil } from "../../util/struct";

export const comp_lab = MapUtil.fromRecord({
  30: {
    position: VectorUtil.fromArray<3>([0, 0, 0]),
    rotation: MatrixUtil.buildMatrix<3, 3>([
      [0, 0, 1],
      [0, 1, 0],
      [-1, 0, 0],
    ]),
  },
});
