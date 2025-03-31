import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseEvent

# Generate x values
x = np.linspace(-2, 8, 100)  # Extended x range to better show the behavior

# Parameters for the exponential function
a = 0.045  # y-intercept scaling
b = 0.6  # growth rate (smaller means slower growth)

# Calculate exponential function y = a * e^(bx)
y = a * np.exp(b * x)

# Create the plot
fig, ax = plt.subplots(figsize=(10, 6))
(line,) = ax.plot(x, y, "b-", label=f"y = {a} * e^({b}x)")
ax.grid(True)
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.set_title("Modified Exponential Function with Slower Growth")
ax.legend()

# Add the x and y axis lines
ax.axhline(y=0, color="k", linestyle="-", alpha=0.3)
ax.axvline(x=0, color="k", linestyle="-", alpha=0.3)

# Set y-axis limit to better show the initial behavior
ax.set_ylim(-0.5, 10)

# Create an annotation that will be updated based on mouse position
annot = ax.annotate(
    "",
    xy=(0, 0),
    xytext=(20, 20),
    textcoords="offset points",
    bbox=dict(boxstyle="round", fc="white", alpha=0.8),
    arrowprops=dict(arrowstyle="->"),
)
annot.set_visible(False)


def find_closest_point(mouseevent):
    """Find the closest point on the line to the mouse position"""
    # Get mouse data coordinates
    mouse_x = mouseevent.xdata
    mouse_y = mouseevent.ydata

    if mouse_x is None or mouse_y is None:
        return None, None, None

    # Find the closest x point in our data
    distances = np.abs(x - mouse_x)
    closest_idx = np.argmin(distances)
    closest_x = x[closest_idx]
    closest_y = y[closest_idx]

    # Calculate distance to the closest point (for threshold)
    screen_distance = np.sqrt((closest_x - mouse_x) ** 2 + (closest_y - mouse_y) ** 2)

    return closest_x, closest_y, screen_distance


def hover(event):
    """Update annotation on hover"""
    if event.inaxes == ax:
        closest_x, closest_y, distance = find_closest_point(event)

        # Only show annotation if mouse is close enough to the line
        if closest_x is not None and distance < 0.5:  # Threshold for showing annotation
            annot.xy = (closest_x, closest_y)
            text = f"x: {closest_x:.2f}\ny: {closest_y:.2f}"
            annot.set_text(text)
            annot.set_visible(True)
            fig.canvas.draw_idle()
        else:
            if annot.get_visible():
                annot.set_visible(False)
                fig.canvas.draw_idle()


# Connect the hover event
fig.canvas.mpl_connect("motion_notify_event", hover)

plt.show()
