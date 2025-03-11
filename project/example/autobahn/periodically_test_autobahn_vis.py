import asyncio
import time
from collections import deque
from statistics import mean
import pygame

from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address


# Store last N measurements for moving average
WINDOW_SIZE = 100
latency_history = deque(maxlen=WINDOW_SIZE)

# Add these new variables for tracking data points
MAX_POINTS = 100
timestamps = deque(maxlen=MAX_POINTS)
latencies = deque(maxlen=MAX_POINTS)
avg_latencies = deque(maxlen=MAX_POINTS)

# Add Pygame visualization constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 400
PADDING = 50
POINT_RADIUS = 2
MAX_LATENCY = 10  # ms - adjusted to 6ms maximum

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Real-time Latency Monitor")


def draw_visualization():
    screen.fill((255, 255, 255))  # White background

    # Draw axes
    pygame.draw.line(
        screen,
        (0, 0, 0),
        (PADDING, SCREEN_HEIGHT - PADDING),
        (SCREEN_WIDTH - PADDING, SCREEN_HEIGHT - PADDING),
    )  # X axis
    pygame.draw.line(
        screen, (0, 0, 0), (PADDING, PADDING), (PADDING, SCREEN_HEIGHT - PADDING)
    )  # Y axis

    # Add scale markers and labels for Y axis
    font = pygame.font.Font(None, 24)
    for i in range(7):  # 0 to 6 ms
        y_pos = SCREEN_HEIGHT - PADDING - (i * (SCREEN_HEIGHT - 2 * PADDING) / 6)
        # Draw tick mark
        pygame.draw.line(screen, (0, 0, 0), (PADDING - 5, y_pos), (PADDING + 5, y_pos))
        # Add label
        label = font.render(f"{i}ms", True, (0, 0, 0))
        screen.blit(label, (PADDING - 40, y_pos - 10))

    # Add scale markers for X axis (time points)
    for i in range(0, MAX_POINTS + 1, 20):  # Mark every 20th point
        x_pos = PADDING + (SCREEN_WIDTH - 2 * PADDING) * (i / MAX_POINTS)
        # Draw tick mark
        pygame.draw.line(
            screen,
            (0, 0, 0),
            (x_pos, SCREEN_HEIGHT - PADDING + 5),
            (x_pos, SCREEN_HEIGHT - PADDING - 5),
        )
        # Add label
        label = font.render(str(i), True, (0, 0, 0))
        screen.blit(label, (x_pos - 10, SCREEN_HEIGHT - PADDING + 10))

    # Plot individual latency points and moving average if we have data
    if latencies and avg_latencies:
        # Plot individual latency points in light blue
        for i, latency in enumerate(latencies):
            x = PADDING + (SCREEN_WIDTH - 2 * PADDING) * (i / MAX_POINTS)
            y = (
                SCREEN_HEIGHT
                - PADDING
                - (SCREEN_HEIGHT - 2 * PADDING) * (latency / MAX_LATENCY)
            )
            pygame.draw.circle(screen, (173, 216, 230), (int(x), int(y)), POINT_RADIUS)

        # Plot moving average line in red
        avg_points = []
        for i, avg_latency in enumerate(avg_latencies):
            x = PADDING + (SCREEN_WIDTH - 2 * PADDING) * (i / MAX_POINTS)
            y = (
                SCREEN_HEIGHT
                - PADDING
                - (SCREEN_HEIGHT - 2 * PADDING) * (avg_latency / MAX_LATENCY)
            )
            avg_points.append((int(x), int(y)))

        # Draw lines connecting average points
        if len(avg_points) > 1:
            pygame.draw.lines(screen, (255, 0, 0), False, avg_points, 2)

    pygame.display.flip()


async def on_ping_received(payload: bytes):
    # Calculate latency first
    timestamp = float(payload.decode("utf-8"))
    current_time = time.time()
    latency = (current_time - timestamp) * 1000  # Convert to milliseconds
    latency_history.append(latency)

    # Store data for plotting
    timestamps.append(current_time)
    latencies.append(latency)
    avg_latency = mean(latency_history) if latency_history else 0
    avg_latencies.append(avg_latency)

    # Print stats
    print(f"Current latency: {latency:.2f}ms")
    print(
        f"Moving average (last {len(latency_history)} measurements): {avg_latency:.2f}ms"
    )


async def main():
    autobahn = Autobahn(Address("localhost", 8090))
    await autobahn.begin()
    await autobahn.subscribe("pong", on_ping_received)

    last_render_time = 0
    render_interval = 0.3  # 300ms
    send_interval = 0.003  # 10ms

    try:
        while True:
            current_time = time.time()

            # Send ping
            timestamp = str(current_time).encode("utf-8")
            await autobahn.publish("pong1", timestamp)

            # Render only every 300ms
            if current_time - last_render_time >= render_interval:
                # Handle Pygame events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        raise KeyboardInterrupt

                # Update visualization
                draw_visualization()
                last_render_time = current_time

            await asyncio.sleep(send_interval)

    except KeyboardInterrupt:
        print("Stopping ping service...")
        pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
