import cv2
import time

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Test actual FPS with a loop
num_frames = 120  # Capture 120 frames for the test
print(f"Capturing {num_frames} frames for FPS test...")

start = time.time()
for i in range(num_frames):
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Optional: Display the frame
    cv2.imshow("FPS Test", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

end = time.time()
elapsed = end - start
actual_fps = num_frames / elapsed

print(f"Time taken: {elapsed:.2f} seconds")
print(f"Actual FPS: {actual_fps:.2f}")

cap.release()
cv2.destroyAllWindows()  # Close any OpenCV windows
