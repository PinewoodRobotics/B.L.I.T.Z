import cv2
import pyapriltags


def get_tag_corners_from_image(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    detector = pyapriltags.Detector(
        families="tag36h11", nthreads=4, quad_decimate=1.0, quad_sigma=0.0
    )
    tags = detector.detect(gray)
    return {tag.tag_id: tag.corners for tag in tags}


def get_tag_corners_from_array(image_array):
    gray = (
        cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        if image_array.ndim == 3
        else image_array
    )
    detector = pyapriltags.Detector(
        families="tag36h11", nthreads=4, quad_decimate=1.0, quad_sigma=0.0
    )
    tags = detector.detect(gray)
    return {tag.tag_id: tag.corners for tag in tags}


corners_by_id = get_tag_corners_from_image("photo_37cm.png")
for tag_id, corners in corners_by_id.items():
    print(f"Tag {tag_id} corners (x,y):\n", corners)
