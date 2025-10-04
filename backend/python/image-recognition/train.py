from ultralytics import YOLO
import os


def train_model():
    # Initialize a YOLOv8n model
    model = YOLO("yolov8n.pt")

    # Train the model
    results = model.train(
        data="dataset/data.yaml",  # Path relative to current directory
        epochs=100,
        imgsz=640,
        batch=8,  # Reduced batch size for CPU
        patience=50,
        save=True,
        device="mps",  # Using MPS for Apple Silicon
        project="runs/train",
        name="exp",
        exist_ok=True,
        pretrained=True,
        optimizer="auto",
        verbose=True,
        seed=42,
        deterministic=True,
        single_cls=False,
        rect=False,
        cos_lr=False,
        close_mosaic=10,
        resume=False,
        amp=True,  # Enable AMP for MPS
        fraction=1.0,
        cache=False,
        nbs=64,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=0.0,
        translate=0.1,
        scale=0.5,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.0,
        copy_paste=0.0,
        auto_augment="randaugment",
        erasing=0.0,
        crop_fraction=1.0,
        overlap_mask=True,
        mask_ratio=4,
    )

    return results


if __name__ == "__main__":
    # Create necessary directories if they don't exist
    os.makedirs("runs/train", exist_ok=True)

    # Train the model
    results = train_model()

    # Print training results
    print("\nTraining completed!")
    if results is not None:
        print(f"Best mAP50: {results.best_map50}")
        print(f"Best epoch: {results.best_epoch}")
    else:
        print("Training failed or was interrupted")
