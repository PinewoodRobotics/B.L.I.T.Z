import cv2

# Open the camera (change 0 to the correct index if needed)
cap = cv2.VideoCapture(0)  # Use CAP_V4L2 for Linux/macOS

# Set resolution to 640x480
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Set FPS to 120
cap.set(cv2.CAP_PROP_FPS, 60)


try:
    while True:
        # Read frame
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Display the frame
        cv2.imshow("Camera Feed", frame)

        # Break loop on 'q' press
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
