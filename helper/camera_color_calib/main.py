import pygame
import cv2
import numpy as np
import os

# Color similarity thresholds (for flood fill)
THRESHOLD_R = 5
THRESHOLD_G = 5
THRESHOLD_B = 5

# Tolerance used when masking based on the global average
GLOBAL_TOLERANCE = 10

# Maximum window dimension
MAX_WINDOW_SIZE = 800


def resize_image(img):
    """Resize image while maintaining aspect ratio"""
    height, width = img.shape[:2]
    if height > MAX_WINDOW_SIZE or width > MAX_WINDOW_SIZE:
        scale = min(MAX_WINDOW_SIZE / width, MAX_WINDOW_SIZE / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        return cv2.resize(img, (new_width, new_height))
    return img


def cv2_flood_fill(img, x, y, masks, screen, colors):
    """
    Uses OpenCV's floodfill for better performance and returns the new mask.
    Appends the selected pixel color (at the seed point) to the passed colors list.
    """
    mask = np.zeros((img.shape[0] + 2, img.shape[1] + 2), dtype=np.uint8)

    # Get original color and calculate lower/upper bounds
    color = img[y, x].copy()
    colors.append(color)
    lo_diff = (THRESHOLD_B, THRESHOLD_G, THRESHOLD_R)
    up_diff = (THRESHOLD_B, THRESHOLD_G, THRESHOLD_R)

    # Perform flood fill (MASK_ONLY: image not altered)
    cv2.floodFill(
        img,
        mask,
        (x, y),
        (255, 0, 0),
        lo_diff,
        up_diff,
        flags=4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY,
    )

    # Remove the padding from the mask
    flood_mask = mask[1:-1, 1:-1]

    # Add new mask to list
    masks.append(flood_mask)

    # Combine all masks for overlay
    combined_mask = np.zeros_like(flood_mask)
    for m in masks:
        combined_mask = cv2.bitwise_or(combined_mask, m)

    # Create a colored overlay for all masks
    overlay = img.copy()
    overlay[combined_mask > 0] = [255, 0, 0]  # Red overlay

    # Blend overlay with original image
    result = cv2.addWeighted(img, 0.7, overlay, 0.3, 0)

    # Convert to pygame surface and display
    result_surface = pygame.surfarray.make_surface(result.transpose(1, 0, 2))
    screen.blit(result_surface, (0, 0))
    pygame.display.flip()

    return flood_mask


def calculate_optimal_color(colors, masks):
    """Calculate optimal color using various statistical methods"""
    colors_np = np.array(colors)

    # Calculate different statistical measures
    mean_color = np.mean(colors_np, axis=0)
    median_color = np.median(colors_np, axis=0)

    # Remove outliers using the IQR method
    Q1 = np.percentile(colors_np, 25, axis=0)
    Q3 = np.percentile(colors_np, 75, axis=0)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    filtered = colors_np[
        np.all((colors_np >= lower_bound) & (colors_np <= upper_bound), axis=1)
    ]
    filtered_mean = np.mean(filtered, axis=0) if len(filtered) > 0 else mean_color

    return {
        "mean_color": mean_color,
        "median_color": median_color,
        "filtered_mean": filtered_mean,
        "sample_count": len(colors_np),
        "filtered_count": len(filtered),
    }


def save_aggregate_results(image_results, all_colors):
    """Save aggregate results from all processed images"""
    with open("aggregate_color_results.txt", "w") as f:
        f.write("Aggregate Color Analysis\n")
        f.write("========================\n\n")

        all_filtered_means = []
        for img_name, results in image_results.items():
            f.write(f"Image: {img_name}\n")
            f.write(f"Filtered Mean Color: {results['filtered_mean']}\n")
            f.write(
                f"Total Samples: {results['sample_count']}, Filtered Samples: {results['filtered_count']}\n\n"
            )
            all_filtered_means.append(results["filtered_mean"])

        if all_filtered_means:
            all_filtered_means_np = np.array(all_filtered_means)
            aggregate_mean = np.mean(all_filtered_means_np, axis=0)
            aggregate_std = np.std(all_filtered_means_np, axis=0)
            f.write("Aggregate Statistics (per-image filtered means):\n")
            f.write(f"Overall Mean Color: {aggregate_mean}\n")
            f.write(f"Color Standard Deviation: {aggregate_std}\n\n")

        # Global stats over all pixel selections across images:
        if all_colors:
            all_colors_np = np.array(all_colors)
            global_mean = np.mean(all_colors_np, axis=0)
            global_std = np.std(all_colors_np, axis=0)
            f.write("Global Aggregated Statistics (all pixel selections):\n")
            f.write(f"Global Mean Color: {global_mean}\n")
            f.write(f"Global Color Standard Deviation: {global_std}\n")
    print("Aggregate results saved to aggregate_color_results.txt")


def main():
    pygame.init()

    folder_path = "captured_images"
    image_files = [
        f
        for f in os.listdir(folder_path)
        if f.lower().endswith((".jpg", ".png", ".jpeg"))
    ]

    if not image_files:
        print("No images found in the specified folder!")
        return

    # Global list to persist pixel colors across images
    all_colors = []

    image_results = {}

    for image_file in image_files:
        img_path = os.path.join(folder_path, image_file)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Could not read image: {image_file}")
            continue

        # Resize image if needed
        img = resize_image(img)

        # Convert BGR to RGB for Pygame display
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        height, width = img.shape[:2]

        # Create Pygame window for current image
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(f"Processing: {image_file}")

        # Create a surface for the original image
        pygame_surface = pygame.surfarray.make_surface(img_rgb.transpose(1, 0, 2))
        screen.blit(pygame_surface, (0, 0))
        pygame.display.flip()

        # Initialize per-image masks and color selections (local colors)
        masks = []
        colors = []  # local to this image

        drawing = False
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
                    return  # exit the entire program

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        running = False
                        pygame.quit()
                        return

                    elif (
                        event.key == pygame.K_c
                    ):  # Clear current image highlighting (masks and local colors)
                        screen.blit(pygame_surface, (0, 0))
                        pygame.display.flip()
                        masks = []
                        colors = []

                    elif (
                        event.key == pygame.K_s
                    ):  # Save current image results and move to next image
                        if masks and colors:
                            # Combine all masks for current image
                            combined_mask = np.zeros_like(masks[0])
                            for m in masks:
                                combined_mask = cv2.bitwise_or(combined_mask, m)

                            # Calculate optimal colors for current image using the local colors list
                            color_stats = calculate_optimal_color(colors, masks)

                            # Use the filtered mean to replace masked regions
                            masked_image = img_rgb.copy()
                            masked_image[combined_mask > 0] = color_stats[
                                "filtered_mean"
                            ]
                            masked_filename = f"masked_{image_file}"
                            cv2.imwrite(
                                masked_filename,
                                cv2.cvtColor(masked_image, cv2.COLOR_RGB2BGR),
                            )

                            # Save color information to a text file
                            color_filename = f"color_info_{image_file}.txt"
                            with open(color_filename, "w") as f:
                                f.write(
                                    f"Mean Color (RGB): {color_stats['mean_color']}\n"
                                )
                                f.write(
                                    f"Median Color (RGB): {color_stats['median_color']}\n"
                                )
                                f.write(
                                    f"Filtered Mean Color (RGB): {color_stats['filtered_mean']}\n"
                                )
                                f.write(
                                    f"Total samples: {color_stats['sample_count']}\n"
                                )
                                f.write(
                                    f"Filtered samples: {color_stats['filtered_count']}\n"
                                )
                                f.write(
                                    f"All sampled colors: {[c.tolist() for c in colors]}"
                                )

                            print(f"Saved masked image as {masked_filename}")
                            print(f"Saved color information as {color_filename}")

                            # Save the per-image stats and add local colors to the global list.
                            image_results[image_file] = color_stats
                            all_colors.extend(colors)

                            # --- Render the Global Masked Image ---
                            # Compute global average across all pixel selections so far.
                            global_avg = np.mean(np.array(all_colors), axis=0)
                            global_avg_int = np.uint8(np.round(global_avg))
                            # Create lower and upper bounds for acceptable colors
                            lower_bound = np.clip(
                                global_avg_int - np.array([GLOBAL_TOLERANCE] * 3),
                                0,
                                255,
                            )
                            upper_bound = np.clip(
                                global_avg_int + np.array([GLOBAL_TOLERANCE] * 3),
                                0,
                                255,
                            )
                            # Generate a mask where pixels in the current image are within the bounds.
                            mask_global = cv2.inRange(img_rgb, lower_bound, upper_bound)
                            # Create an image with white background
                            global_masked_img = np.full_like(
                                img_rgb, 255
                            )  # White background
                            # Only copy the masked pixels, leaving others white
                            global_masked_img[mask_global > 0] = img_rgb[
                                mask_global > 0
                            ]

                            # Display the global masked image
                            result_surface = pygame.surfarray.make_surface(
                                global_masked_img.transpose(1, 0, 2)
                            )
                            screen.blit(result_surface, (0, 0))
                            pygame.display.flip()

                            # Save the global masked image.
                            global_masked_filename = f"global_masked_{image_file}"
                            cv2.imwrite(
                                global_masked_filename,
                                cv2.cvtColor(global_masked_img, cv2.COLOR_RGB2BGR),
                            )
                            print(
                                f"Saved global masked image as {global_masked_filename}"
                            )

                        else:
                            print("No masks/colors to save for this image.")

                        # Exit loop for this image (move on to next)
                        running = False

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        drawing = True
                        x, y = event.pos
                        if 0 <= x < width and 0 <= y < height:
                            cv2_flood_fill(img_rgb, x, y, masks, screen, colors)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        drawing = False
                elif event.type == pygame.MOUSEMOTION and drawing:
                    x, y = event.pos
                    if 0 <= x < width and 0 <= y < height:
                        cv2_flood_fill(img_rgb, x, y, masks, screen, colors)

        # Clean up the current window and reinitialize for the next image
        pygame.display.quit()
        pygame.display.init()

    # After processing all images, save aggregate results.
    save_aggregate_results(image_results, all_colors)
    pygame.quit()


if __name__ == "__main__":
    main()
