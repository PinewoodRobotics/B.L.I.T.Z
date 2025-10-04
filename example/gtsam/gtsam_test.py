import gtsam
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import random


class InteractiveGTSAMDemo:
    def __init__(self):
        self.graph = gtsam.NonlinearFactorGraph()
        self.initial_estimate = gtsam.Values()
        self.poses = []
        self.landmarks = []
        self.pose_count = 0
        self.landmark_count = 0

        self.prior_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.3, 0.3, 0.1]))
        self.odometry_noise = gtsam.noiseModel.Diagonal.Sigmas(
            np.array([0.2, 0.2, 0.1])
        )
        self.measurement_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.1, 0.1]))

    def add_prior_pose(self, x, y, theta):
        pose_key = gtsam.symbol("x", self.pose_count)
        pose = gtsam.Pose2(x, y, theta)

        self.graph.add(gtsam.PriorFactorPose2(pose_key, pose, self.prior_noise))
        self.initial_estimate.insert(pose_key, pose)
        self.poses.append((pose_key, pose))
        self.pose_count += 1
        print(
            f"Added prior pose {self.pose_count-1} at ({x:.2f}, {y:.2f}, {theta:.2f})"
        )

    def add_odometry(self, dx, dy, dtheta, add_noise=False):
        if self.pose_count < 1:
            print("Need at least 1 pose for odometry")
            return

        pose_key1 = gtsam.symbol("x", self.pose_count - 1)
        pose_key2 = gtsam.symbol("x", self.pose_count)

        if add_noise:
            noise_dx = dx + random.gauss(0, 0.1)
            noise_dy = dy + random.gauss(0, 0.1)
            noise_dtheta = dtheta + random.gauss(0, 0.05)
            odometry = gtsam.Pose2(noise_dx, noise_dy, noise_dtheta)
            print(
                f"Added noise to odometry: ({noise_dx:.3f}, {noise_dy:.3f}, {noise_dtheta:.3f})"
            )
        else:
            odometry = gtsam.Pose2(dx, dy, dtheta)

        self.graph.add(
            gtsam.BetweenFactorPose2(
                pose_key1, pose_key2, odometry, self.odometry_noise
            )
        )

        current_pose = self.initial_estimate.atPose2(pose_key1)
        new_pose = current_pose.compose(odometry)
        self.initial_estimate.insert(pose_key2, new_pose)
        self.poses.append((pose_key2, new_pose))
        self.pose_count += 1
        print(
            f"Added odometry from pose {self.pose_count-2} to {self.pose_count-1}: ({dx:.2f}, {dy:.2f}, {dtheta:.2f})"
        )

    def add_landmark(self, x, y):
        landmark_key = gtsam.symbol("l", self.landmark_count)
        landmark = gtsam.Point2(x, y)

        self.initial_estimate.insert(landmark_key, landmark)
        self.landmarks.append((landmark_key, landmark))
        self.landmark_count += 1
        print(f"Added landmark {self.landmark_count-1} at ({x:.2f}, {y:.2f})")

    def add_measurement(self, pose_idx, landmark_idx, bearing, range_measurement):
        print(
            "Measurement functionality simplified - using basic pose graph optimization"
        )
        print(
            f"Would add measurement: pose {pose_idx} to landmark {landmark_idx} (bearing: {bearing:.2f}, range: {range_measurement:.2f})"
        )

    def optimize(self):
        if self.graph.size() == 0:
            print("No factors in graph to optimize")
            return None

        optimizer = gtsam.LevenbergMarquardtOptimizer(self.graph, self.initial_estimate)
        result = optimizer.optimize()

        print(f"Optimization complete! Final error: {self.graph.error(result):.6f}")
        return result

    def plot_results(self, result=None, interactive=False):
        if result is None:
            result = self.initial_estimate

        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111)

        pose_x = []
        pose_y = []
        landmark_x = []
        landmark_y = []

        for i in range(self.pose_count):
            pose_key = gtsam.symbol("x", i)
            if result.exists(pose_key):
                pose = result.atPose2(pose_key)
                pose_x.append(pose.x())
                pose_y.append(pose.y())

        for i in range(self.landmark_count):
            landmark_key = gtsam.symbol("l", i)
            if result.exists(landmark_key):
                landmark = result.atPoint2(landmark_key)
                landmark_x.append(landmark[0])
                landmark_y.append(landmark[1])

        if pose_x:
            ax.plot(pose_x, pose_y, "bo-", label="Poses", linewidth=2, markersize=8)
            for i, (x, y) in enumerate(zip(pose_x, pose_y)):
                ax.annotate(f"P{i}", (x, y), xytext=(5, 5), textcoords="offset points")

        if landmark_x:
            ax.scatter(
                landmark_x, landmark_y, c="red", s=100, label="Landmarks", marker="*"
            )
            for i, (x, y) in enumerate(zip(landmark_x, landmark_y)):
                ax.annotate(f"L{i}", (x, y), xytext=(5, 5), textcoords="offset points")

        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_title("GTSAM Factor Graph Results")
        ax.legend()
        ax.grid(True)
        ax.axis("equal")

        if interactive:
            ax.set_xlim(-5, 10)
            ax.set_ylim(-5, 10)
            print("Click on the plot to add landmarks. Close the window when done.")

            def on_click(event):
                if event.inaxes == ax:
                    x, y = event.xdata, event.ydata
                    if x is not None and y is not None:
                        self.add_landmark(x, y)
                        print(f"Added landmark at ({x:.2f}, {y:.2f})")

                        landmark_key = gtsam.symbol("l", self.landmark_count - 1)
                        landmark = gtsam.Point2(x, y)
                        ax.scatter(x, y, c="red", s=100, marker="*")
                        ax.annotate(
                            f"L{self.landmark_count-1}",
                            (x, y),
                            xytext=(5, 5),
                            textcoords="offset points",
                        )
                        plt.draw()

            fig.canvas.mpl_connect("button_press_event", on_click)

        plt.show()


def main():
    demo = InteractiveGTSAMDemo()

    print("=== Interactive GTSAM Demo ===")
    print("Commands:")
    print("1. add_prior x y theta - Add a prior pose")
    print(
        "2. add_odom dx dy dtheta [noise] - Add odometry between poses (add 'noise' for random noise)"
    )
    print("3. add_landmark x y - Add a landmark")
    print("4. add_measurement pose_idx landmark_idx bearing range - Add measurement")
    print("5. optimize - Run optimization")
    print("6. plot - Plot current results")
    print("7. plot_interactive - Plot with clickable landmarks")
    print("8. demo - Run a simple demo")
    print("9. demo_noisy - Run demo with random noise")
    print("10. quit - Exit")

    while True:
        try:
            command = input("\nEnter command: ").strip().split()
            if not command:
                continue

            cmd = command[0].lower()

            if cmd == "add_prior":
                if len(command) == 4:
                    x, y, theta = map(float, command[1:])
                    demo.add_prior_pose(x, y, theta)
                else:
                    print("Usage: add_prior x y theta")

            elif cmd == "add_odom":
                if len(command) == 4:
                    dx, dy, dtheta = map(float, command[1:])
                    demo.add_odometry(dx, dy, dtheta)
                elif len(command) == 5 and command[4].lower() == "noise":
                    dx, dy, dtheta = map(float, command[1:4])
                    demo.add_odometry(dx, dy, dtheta, add_noise=True)
                else:
                    print("Usage: add_odom dx dy dtheta [noise]")

            elif cmd == "add_landmark":
                if len(command) == 3:
                    x, y = map(float, command[1:])
                    demo.add_landmark(x, y)
                else:
                    print("Usage: add_landmark x y")

            elif cmd == "add_measurement":
                if len(command) == 5:
                    pose_idx, landmark_idx, bearing, range_val = map(float, command[1:])
                    demo.add_measurement(
                        int(pose_idx), int(landmark_idx), bearing, range_val
                    )
                else:
                    print("Usage: add_measurement pose_idx landmark_idx bearing range")

            elif cmd == "optimize":
                result = demo.optimize()
                if result:
                    print("Optimization successful!")

            elif cmd == "plot":
                demo.plot_results()

            elif cmd == "plot_interactive":
                demo.plot_results(interactive=True)

            elif cmd == "demo":
                print("Running simple demo...")
                demo.add_prior_pose(0, 0, 0)
                demo.add_odometry(1, 0, 0)
                demo.add_odometry(1, 0, 0)
                demo.add_landmark(2, 1)
                demo.add_landmark(2, -1)
                result = demo.optimize()
                demo.plot_results(result)

            elif cmd == "demo_noisy":
                print("Running noisy demo...")
                demo.add_prior_pose(0, 0, 0)
                demo.add_odometry(1, 0, 0, add_noise=True)
                demo.add_odometry(1, 0, 0, add_noise=True)
                demo.add_landmark(2, 1)
                demo.add_landmark(2, -1)
                result = demo.optimize()
                demo.plot_results(result)

            elif cmd == "quit":
                print("Goodbye!")
                break

            else:
                print("Unknown command. Type 'quit' to exit.")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
