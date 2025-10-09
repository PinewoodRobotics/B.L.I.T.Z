import time
import cv2
import numpy as np
import pyapriltags

CAMERA_MATRIX = np.array([
    [644.12542785, 0., 318.47939346],
    [0., 639.36517808, 218.74994066],
    [0., 0., 1.],
])
DIST_COEFF = np.array([-0.43899338, 0.33405716, 0.00489076, -0.00426836, -0.3116031])
TAG_SIZE_M = 0.16
real_world_corners = np.array([
    [-TAG_SIZE_M / 2, -TAG_SIZE_M / 2], # top left
    [TAG_SIZE_M / 2, -TAG_SIZE_M / 2], # top right
    [-TAG_SIZE_M / 2, TAG_SIZE_M / 2], # bottom left
    [TAG_SIZE_M / 2, TAG_SIZE_M / 2], # bottom right
], dtype=np.float32)

def get_detector():
    return pyapriltags.Detector(
        families="tag36h11",
        nthreads=4,
        quad_decimate=1.0,
        quad_sigma=0.0,
    )

def solve_position(corners: np.ndarray, tag_size: float, camera_matrix: np.ndarray, dist_coeff: np.ndarray):
    # start_time = time.time()
    undistorted_points = cv2.undistortPoints(corners, camera_matrix, dist_coeff)
    undistorted_points = (undistorted_points @ camera_matrix[:2, :2].T) + camera_matrix[:2, 2]
    
    obj_pts = np.array([
        [-tag_size/2, -tag_size/2, 0],
        [ tag_size/2, -tag_size/2, 0],
        [ tag_size/2,  tag_size/2, 0],
        [-tag_size/2,  tag_size/2, 0]
    ], dtype=np.float32)

    ret, rvec, tvec = cv2.solvePnP(obj_pts, undistorted_points.reshape(4,1,2), camera_matrix, dist_coeff, flags=cv2.SOLVEPNP_ITERATIVE)
    tvec = tvec.flatten() if tvec is not None else None
    rvec = rvec.flatten() if rvec is not None else None
    _ = time.time()
    print(undistorted_points)
    return tvec, rvec

def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    detector = get_detector()
    
    while True:
        ret, frame = cap.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fx, fy, cx, cy = (
            CAMERA_MATRIX[0, 0],
            CAMERA_MATRIX[1, 1],
            CAMERA_MATRIX[0, 2],
            CAMERA_MATRIX[1, 2],
        )
        unfisheye_image = cv2.undistort(gray, CAMERA_MATRIX, DIST_COEFF)
        tags = detector.detect(unfisheye_image, estimate_tag_pose=True, camera_params=((fx, fy, cx, cy)), tag_size=TAG_SIZE_M)
        tags1 = detector.detect(gray)
        for tag in tags:
            for corner in tag.corners:
                cv2.circle(frame, (int(corner[0]), int(corner[1])), 5, (0, 0, 255), -1)
            if tag.pose_t is not None and tag.pose_R is not None:
                text1 = f"x: {float(tag.pose_t[0]):.4f}, y: {float(tag.pose_t[1]):.4f}, z: {float(tag.pose_t[2]):.4f}"
                cv2.putText(frame, text1, (int(tag.corners[0][0]) + 20, int(tag.corners[0][1]) + 20), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        for tag in tags1:
            tvec, rvec = solve_position(tag.corners, TAG_SIZE_M, CAMERA_MATRIX, DIST_COEFF)
            text = f"x: {float(tvec[0]):.4f}, y: {float(tvec[1]):.4f}, z: {float(tvec[2]):.4f}"
            cv2.putText(frame, text, (int(tag.corners[0][0]), int(tag.corners[0][1])), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            # cv2.circle(frame, (int(corner[0]), int(corner[1])), 5, (0, 0, 255), -1)
        cv2.imshow("frame", frame)
        cv2.waitKey(1)

if __name__ == "__main__":
    main()
