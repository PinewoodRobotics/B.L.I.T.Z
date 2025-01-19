from filterpy.kalman import KalmanFilter
import numpy as np
import matplotlib.pyplot as plt

# Initialize Kalman Filter
kf = KalmanFilter(
    dim_x=5,
    dim_z=5,
)  # State: [x, y, vx, vy, theta], Measurements: [x, y, vx, vy, theta]

# State vector: [x, y, vx, vy]
kf.x = np.array([0.0, 0.0, 0.0, 0.0, 0.0])

# State transition matrix (constant velocity model)
dt = 0.1  # Time step
kf.F = np.array(
    [
        [1, 0, dt, 0, 0],
        [0, 1, 0, dt, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 0, 1],
    ]
)

# Measurement function (maps state to measurement space)
kf.H = np.array(
    [
        [1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 0, 1],
    ]
)

# Covariance matrices
kf.P = np.eye(5) * 500  # Initial uncertainty
kf.Q = np.array(
    [
        [0.1, 0, 0, 0, 0],  # x
        [0, 0.1, 0, 0, 0],  # y
        [0, 0, 0.1, 0, 0],  # vx
        [0, 0, 0, 0.1, 0],  # vy
        [0, 0, 0, 0, 0.1],  # theta
    ]
)

# Sensor-specific measurement noise covariance matrices
R_apriltag = np.array(
    [
        [1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 0, 1],
    ]
)  # AprilTags
R_odometry = np.array(
    [
        [0.5, 0, 0, 0, 0],
        [0, 0.5, 0, 0, 0],
        [0, 0, 0.5, 0, 0],
        [0, 0, 0, 0.5, 0],
        [0, 0, 0, 0, 0.5],
    ]
)  # Odometry

# Generate true trajectory (ground truth)
t = np.linspace(0, 10, 70)  # 70 points over spiral
growth = 0.2  # Controls how quickly spiral grows
true_x = t * np.cos(t) * growth  # Spiral x coordinate
true_y = t * np.sin(t) * growth  # Spiral y coordinate
# Calculate velocities as derivatives of position
true_vx = np.cos(t) * growth - t * np.sin(t) * growth  # d(x)/dt
true_vy = np.sin(t) * growth + t * np.cos(t) * growth  # d(y)/dt
true_theta = np.arctan2(true_vy, true_vx)  # orientation based on velocity direction

# Generate noisy AprilTag measurements (less frequent updates, more noise)
apriltag_indices = np.arange(0, len(t), 3)  # Sample every 3rd point
apriltag_measurements = np.array(
    [
        [
            true_x[i] + np.random.normal(0, 0.2),
            true_y[i] + np.random.normal(0, 0.2),
            true_vx[i] + np.random.normal(0, 0.1),
            true_vy[i] + np.random.normal(0, 0.1),
            true_theta[i] + np.random.normal(0, 0.05),
        ]
        for i in apriltag_indices
    ]
)

# Generate noisy odometry measurements (more frequent updates, less noise)
odometry_measurements = np.array(
    [
        [
            true_x[i] + np.random.normal(0, 0.1),
            true_y[i] + np.random.normal(0, 0.1),
            true_vx[i] + np.random.normal(0, 0.05),
            true_vy[i] + np.random.normal(0, 0.05),
            true_theta[i] + np.random.normal(0, 0.02),
        ]
        for i in range(len(t))
    ]
)

# Lists to store positions for plotting
apriltag_xs, apriltag_ys = [], []
odometry_xs, odometry_ys = [], []
kalman_xs, kalman_ys = [], []
avg_xs = []
avg_ys = []
weighted_avg_xs = []  # New list for weighted average
weighted_avg_ys = []  # New list for weighted average

# Define weights for sensor fusion
APRILTAG_WEIGHT = 0.7
ODOMETRY_WEIGHT = 0.3  # Note: Should sum to 1.0 with APRILTAG_WEIGHT

# Process the measurements
for i in range(len(t)):
    # Process odometry measurements (available at every timestep)
    odometry_xs.append(odometry_measurements[i][0])
    odometry_ys.append(odometry_measurements[i][1])

    kf.predict()

    # Process AprilTag measurements (only available every 3rd timestep)
    if i in apriltag_indices:
        apriltag_idx = np.where(apriltag_indices == i)[0][0]
        apriltag_xs.append(apriltag_measurements[apriltag_idx][0])
        apriltag_ys.append(apriltag_measurements[apriltag_idx][1])
        kf.update(apriltag_measurements[apriltag_idx], R=R_apriltag)

        # Calculate weighted average when both measurements are available
        weighted_x = (
            APRILTAG_WEIGHT * apriltag_measurements[apriltag_idx][0]
            + ODOMETRY_WEIGHT * odometry_measurements[i][0]
        )
        weighted_y = (
            APRILTAG_WEIGHT * apriltag_measurements[apriltag_idx][1]
            + ODOMETRY_WEIGHT * odometry_measurements[i][1]
        )
    else:
        # When only odometry is available, use it alone
        weighted_x = odometry_measurements[i][0]
        weighted_y = odometry_measurements[i][1]

    weighted_avg_xs.append(weighted_x)
    weighted_avg_ys.append(weighted_y)

    # Store Kalman filter estimates
    kalman_xs.append(kf.x[0])
    kalman_ys.append(kf.x[1])

    # Calculate and store simple average of available measurements
    current_x_measurements = [odometry_measurements[i][0]]
    current_y_measurements = [odometry_measurements[i][1]]
    if i in apriltag_indices:
        apriltag_idx = np.where(apriltag_indices == i)[0][0]
        current_x_measurements.append(apriltag_measurements[apriltag_idx][0])
        current_y_measurements.append(apriltag_measurements[apriltag_idx][1])

    avg_xs.append(np.mean(current_x_measurements))
    avg_ys.append(np.mean(current_y_measurements))

# Plot the results
plt.figure(figsize=(15, 5))

# First subplot - Kalman Filter
plt.subplot(1, 3, 1)
plt.plot(true_x, true_y, "k-", label="Ground Truth", linewidth=2)
plt.plot(apriltag_xs, apriltag_ys, "r*", label="AprilTag Measurements")
plt.plot(odometry_xs, odometry_ys, "g+", label="Odometry Measurements")
plt.plot(kalman_xs, kalman_ys, "b-o", label="Kalman Filter Estimate")
plt.legend()
plt.grid(True)
plt.xlabel("X Position")
plt.ylabel("Y Position")
plt.title("Kalman Filter Tracking")
plt.axis("equal")

# Second subplot - Simple Average
plt.subplot(1, 3, 2)
plt.plot(true_x, true_y, "k-", label="Ground Truth", linewidth=2)
plt.plot(apriltag_xs, apriltag_ys, "r*", label="AprilTag Measurements")
plt.plot(odometry_xs, odometry_ys, "g+", label="Odometry Measurements")
plt.plot(avg_xs, avg_ys, "m--", label="Simple Average")
plt.legend()
plt.grid(True)
plt.xlabel("X Position")
plt.ylabel("Y Position")
plt.title("Simple Average Tracking")
plt.axis("equal")

# Third subplot - Weighted Average
plt.subplot(1, 3, 3)
plt.plot(true_x, true_y, "k-", label="Ground Truth", linewidth=2)
plt.plot(apriltag_xs, apriltag_ys, "r*", label="AprilTag Measurements")
plt.plot(odometry_xs, odometry_ys, "g+", label="Odometry Measurements")
plt.plot(weighted_avg_xs, weighted_avg_ys, "c--", label="Weighted Average")
plt.legend()
plt.grid(True)
plt.xlabel("X Position")
plt.ylabel("Y Position")
plt.title("Weighted Average Tracking")
plt.axis("equal")

plt.tight_layout()
plt.show()
