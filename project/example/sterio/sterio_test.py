import time
import cv2
import numpy as np

# Load your two frames
frame1 = cv2.imread("left.png", cv2.IMREAD_GRAYSCALE)
frame2 = cv2.imread("right.png", cv2.IMREAD_GRAYSCALE)

orb = cv2.ORB_create()

start_time = time.time()

# Step 2: Detect keypoints and descriptors
kp1, des1 = orb.detectAndCompute(frame1, None)
kp2, des2 = orb.detectAndCompute(frame2, None)

# Step 3: Match descriptors using a matcher
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)  # ORB uses Hamming distance
matches = bf.match(des1, des2)

# Step 4: Sort matches by distance (lower distance = better match)
matches = sorted(matches, key=lambda x: x.distance)

# (Optional) Draw first 50 matches
match_img = cv2.drawMatches(frame1, kp1, frame2, kp2, matches, None, flags=2)

end_time = time.time()
print(f"Time taken: {(end_time - start_time) * 1000} ms")

# Show
cv2.imshow("Matches", match_img)
cv2.waitKey(0)
cv2.destroyAllWindows()
