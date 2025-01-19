import pygame
import sys
from collections import deque

# Initialize Pygame
pygame.init()

# Set up the display
WIDTH = 800
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bouncing Ball with Trail")

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
TRAIL_COLOR = (255, 192, 203)  # Light pink trail

# Ball properties
ball_radius = 10  # Smaller ball
ball_x = WIDTH // 2
ball_y = HEIGHT // 2
ball_speed_x = 90
ball_speed_y = 90

# Trail properties
trail_length = 50  # Number of positions to remember
trail_positions = deque(maxlen=trail_length)

# Game clock
clock = pygame.time.Clock()

# Game loop
while True:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    # Update ball position
    ball_x += ball_speed_x
    ball_y += ball_speed_y

    # Add current position to trail
    trail_positions.append((int(ball_x), int(ball_y)))

    # Ball collision with walls
    if ball_x <= ball_radius or ball_x >= WIDTH - ball_radius:
        ball_speed_x = -ball_speed_x
    if ball_y <= ball_radius or ball_y >= HEIGHT - ball_radius:
        ball_speed_y = -ball_speed_y

    # Clear screen
    screen.fill(WHITE)

    # Draw trail
    if len(trail_positions) > 1:
        pygame.draw.lines(screen, TRAIL_COLOR, False, list(trail_positions), 2)

    # Draw ball
    pygame.draw.circle(screen, RED, (int(ball_x), int(ball_y)), ball_radius)

    # Update display
    pygame.display.flip()

    # Control frame rate (60 FPS)
    clock.tick(15)
