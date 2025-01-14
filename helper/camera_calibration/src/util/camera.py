import cv2
import numpy as np
import pyapriltags

from config.transformation import (
    QuadDetection,
    TransformationConfig,
)


def undistort_image(
    image: np.ndarray, camera_matrix: list[list[float]], dist_coeff: list[float]
):
    camera_matrix_arr = np.array(camera_matrix)
    dist_coeff_arr = np.array(dist_coeff)
    height, width = image.shape[:2]
    newcameramtx, roi = cv2.getOptimalNewCameraMatrix(
        camera_matrix_arr, dist_coeff_arr, (width, height), 1, (width, height)
    )

    dst = cv2.undistort(image, camera_matrix_arr, dist_coeff_arr, None, newcameramtx)
    x, y, w, h = roi
    dst = dst[y : y + h, x : x + w]

    max_dim = 800
    scale = max_dim / max(dst.shape[0], dst.shape[1])
    if scale < 1:
        dst = cv2.resize(dst, None, fx=scale, fy=scale)

    return dst


def detect_april_tags(
    image: np.ndarray,
    tag_size_m: float,
    camera_params: tuple[float, float, float, float],
    detector: pyapriltags.Detector,
):
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    tags = detector.detect(
        image,
        estimate_tag_pose=True,
        camera_params=camera_params,
        tag_size=tag_size_m,
    )

    return tags


def apply_all_transformations(
    image: np.ndarray,
    config: TransformationConfig,
    camera_params: tuple[float, float, float, float],
    detector: pyapriltags.Detector,
):
    if config.undistort:
        image = undistort_image(
            image, config.undistort.camera_matrix, config.undistort.dist_coeff
        )
    if config.use_grayscale:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    image = config.threshholding.apply(image)

    if config.detect_april_tags:
        image = render_april_tags(
            image,
            detect_april_tags(
                image, config.april_tag_config.tag_size_m, camera_params, detector
            ),
        )
    return image


def render_april_tags(image: np.ndarray, tags: list[pyapriltags.Detection]):
    for tag in tags:
        cv2.circle(image, (int(tag.center[0]), int(tag.center[1])), 4, (0, 255, 0), -1)

        if (
            tag.pose_R is not None
            and tag.pose_t is not None
            and tag.tag_size is not None
        ):
            rvec = cv2.Rodrigues(tag.pose_R)[0]
            tvec = tag.pose_t

            axis_length = tag.tag_size * 1.5
            axis_points = np.float32(
                [
                    [0.0, 0.0, 0.0],
                    [axis_length, 0.0, 0.0],
                    [0.0, axis_length, 0.0],
                    [0.0, 0.0, axis_length],
                ]  # type: ignore
            )

            fx = tag.pose_R[0][0]
            fy = tag.pose_R[1][1]
            cx = tag.center[0]
            cy = tag.center[1]
            camera_matrix = np.array(
                [[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float32
            )

            dist_coeffs = np.zeros(4)

            img_points, _ = cv2.projectPoints(
                axis_points, rvec, tvec, camera_matrix, dist_coeffs  # type: ignore
            )  # type: ignore
            img_points = img_points.reshape(-1, 2)

            origin = tuple(map(int, img_points[0]))
            x_point = tuple(map(int, img_points[1]))
            y_point = tuple(map(int, img_points[2]))
            z_point = tuple(map(int, img_points[3]))

            cv2.line(image, origin, x_point, (0, 0, 255), 2)
            cv2.line(image, origin, y_point, (0, 255, 0), 2)
            cv2.line(image, origin, z_point, (255, 0, 0), 2)

    return image
