import numpy as np
import matplotlib.pyplot as plt


def generate_fake_data(num_steps=100, dt=0.1):
    """
    Generate fake data for AprilTags, odom, and IMU to test a Kalman filter.
    Uses randomly selected non-linear trajectories.

    Parameters:
        num_steps (int): Number of time steps for the generated data.
        dt (float): Time step interval.

    Returns:
        dict: A dictionary containing AprilTag, odom, and IMU data.
    """
    np.random.seed(42)  # For reproducibility

    # True state: [x, y, vx, vy, theta] (position, velocity, orientation)
    true_state = np.zeros((num_steps, 5))
    measurements = {"april_tag": [], "odom": [], "imu": []}

    # Randomly select a trajectory type
    trajectory_type = np.random.choice(["circle", "figure_eight", "spiral"])

    # Parameters for trajectories
    t = np.linspace(0, 10, num_steps)
    if trajectory_type == "circle":
        radius = 2.0
        frequency = 0.5
        true_state[:, 0] = radius * np.cos(frequency * t)
        true_state[:, 1] = radius * np.sin(frequency * t)
        # Velocities are derivatives of position
        true_state[:, 2] = -radius * frequency * np.sin(frequency * t)
        true_state[:, 3] = radius * frequency * np.cos(frequency * t)
    elif trajectory_type == "figure_eight":
        scale = 2.0
        true_state[:, 0] = scale * np.sin(t)
        true_state[:, 1] = scale * np.sin(t) * np.cos(t)
        true_state[:, 2] = scale * np.cos(t)
        true_state[:, 3] = scale * (np.cos(t) ** 2 - np.sin(t) ** 2)
    else:  # spiral
        growth = 0.1
        true_state[:, 0] = t * np.cos(t) * growth
        true_state[:, 1] = t * np.sin(t) * growth
        true_state[:, 2] = np.cos(t) * growth - t * np.sin(t) * growth
        true_state[:, 3] = np.sin(t) * growth + t * np.cos(t) * growth

    # Calculate orientation (theta) based on velocity direction
    true_state[:, 4] = np.arctan2(true_state[:, 3], true_state[:, 2])

    # Noise parameters
    process_noise = np.array([0.1, 0.1, 0.05, 0.05, 0.01])
    april_tag_noise = np.array([0.15, 0.15])
    odom_noise = np.array([0.1, 0.1, 0.02])
    imu_noise = 0.01

    # Add noise and generate measurements
    for t in range(1, num_steps):
        # Add process noise to true state
        true_state[t, :] += np.random.normal(0, process_noise)

        # Generate AprilTag measurements (position only)
        april_tag_x = true_state[t, 0] + np.random.normal(0, april_tag_noise[0])
        april_tag_y = true_state[t, 1] + np.random.normal(0, april_tag_noise[1])
        measurements["april_tag"].append((april_tag_x, april_tag_y))

        # Generate odometry measurements (velocity and orientation)
        odom_vx = true_state[t, 2] + np.random.normal(0, odom_noise[0])
        odom_vy = true_state[t, 3] + np.random.normal(0, odom_noise[1])
        odom_theta = true_state[t, 4] + np.random.normal(0, odom_noise[2])
        measurements["odom"].append((odom_vx, odom_vy, odom_theta))

        # Generate IMU measurements (angular velocity)
        imu_angular_velocity = (
            true_state[t, 4] - true_state[t - 1, 4]
        ) / dt + np.random.normal(0, imu_noise)
        measurements["imu"].append(imu_angular_velocity)

    return measurements


def plot_fake_data(measurements):
    """
    Plot the generated fake data on a 2D plane.

    Parameters:
        measurements (dict): Dictionary containing AprilTag, odom, and IMU data.
    """

    # Extract AprilTag positions
    april_tag_positions = np.array(measurements["april_tag"])

    # Create the plot
    plt.figure(figsize=(10, 8))

    # Plot AprilTag measurements
    plt.scatter(
        april_tag_positions[:, 0],
        april_tag_positions[:, 1],
        c="blue",
        label="AprilTag Measurements",
        alpha=0.5,
    )

    # Calculate and plot odometry path
    odom_positions = np.zeros((len(measurements["odom"]), 2))
    odom_positions[0] = april_tag_positions[0]  # Start from first AprilTag position
    dt = 0.1  # Same dt as in generate_fake_data

    for i in range(1, len(measurements["odom"])):
        vx, vy, _ = measurements["odom"][i - 1]
        odom_positions[i] = odom_positions[i - 1] + np.array([vx, vy]) * dt

    plt.plot(
        odom_positions[:, 0],
        odom_positions[:, 1],
        "r-",
        label="Odometry Path",
        alpha=0.7,
    )

    plt.title("Simulated Robot Position Data")
    plt.xlabel("X Position")
    plt.ylabel("Y Position")
    plt.legend()
    plt.grid(True)
    plt.axis("equal")
    plt.show()


measurements = generate_fake_data()
plot_fake_data(measurements)
