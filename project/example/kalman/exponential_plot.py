import numpy as np
import matplotlib.pyplot as plt

# Generate x values
x = np.linspace(-2, 8, 100)  # Extended x range to better show the behavior

# Parameters for the exponential function
a = 1.0  # y-intercept scaling
b = 0.6  # growth rate (smaller means slower growth)

# Calculate exponential function y = a * e^(bx)
y = a * np.exp(b * x)

# Create the plot
plt.figure(figsize=(10, 6))
plt.plot(x, y, "b-", label=f"y = {a} * e^({b}x)")
plt.grid(True)
plt.xlabel("x")
plt.ylabel("y")
plt.title("Modified Exponential Function with Slower Growth")
plt.legend()

# Add the x and y axis lines
plt.axhline(y=0, color="k", linestyle="-", alpha=0.3)
plt.axvline(x=0, color="k", linestyle="-", alpha=0.3)

# Set y-axis limit to better show the initial behavior
plt.ylim(-0.5, 10)

plt.show()
