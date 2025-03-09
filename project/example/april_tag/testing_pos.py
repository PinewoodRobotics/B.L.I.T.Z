import math
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

VISUALIZATION_SCALE = 100  # pixels per meter
VIS_SIZE = 400  # pixels

def get_detector():
    return pyapriltags.Detector(
        families="tag36h11",
        nthreads=4,
        quad_decimate=1.0,
        quad_sigma=0.0,
    )

def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    detector = get_detector()

    # Create top-down visualization window
    vis = np.ones((VIS_SIZE, VIS_SIZE, 3), dtype=np.uint8) * 255
    
    while True:
        ret, frame = cap.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fx, fy, cx, cy = (
            CAMERA_MATRIX[0, 0],
            CAMERA_MATRIX[1, 1],
            CAMERA_MATRIX[0, 2],
            CAMERA_MATRIX[1, 2],
        )
        tags = detector.detect(gray, estimate_tag_pose=True, camera_params=(fx, fy, cx, cy), tag_size=TAG_SIZE_M)

        # Clear visualization
        vis.fill(255)
        # Draw coordinate system
        center = VIS_SIZE // 2
        cv2.line(vis, (center, 0), (center, VIS_SIZE), (200, 200, 200), 1)
        cv2.line(vis, (0, center), (VIS_SIZE, center), (200, 200, 200), 1)

        for tag in tags:
            for corner in tag.corners:
                cv2.circle(frame, (int(corner[0]), int(corner[1])), 5, (0, 0, 255), -1)
            
            camera_position, rot_matrix = tag.pose_t, tag.pose_R
            if camera_position is not None and rot_matrix is not None:
                # Camera view text
                text = f"x: {float(camera_position[0]):.2f}, y: {float(camera_position[1]):.2f}, z: {float(camera_position[2]):.2f}"
                cv2.putText(frame, text, (int(tag.corners[0][0]), int(tag.corners[0][1])), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Top-down view
                px = int(center + camera_position[0] * VISUALIZATION_SCALE)
                py = int(center - camera_position[2] * VISUALIZATION_SCALE)  # Using z for forward direction
                
                # Draw camera position
                cv2.circle(vis, (px, py), 5, (0, 0, 255), -1)
                
                # Calculate heading from rotation matrix
                heading = math.atan2(rot_matrix[2, 0], rot_matrix[0, 0])
                
                # Draw camera direction
                direction_x = int(20 * math.cos(heading))
                direction_y = int(-20 * math.sin(heading))
                cv2.line(vis, (px, py), (px + direction_x, py + direction_y), (0, 0, 255), 2)
                
                # Draw tag ID
                cv2.putText(vis, f"Tag {tag.tag_id}", (px + 10, py + 10), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        cv2.imshow("Camera View", frame)
        cv2.imshow("Top-Down View", vis)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

if __name__ == "__main__":
    main()
