"""
YOLOv8 nano training script for ATM surveillance model.

Usage::

    # Basic training
    python training/train.py

    # Custom settings
    python training/train.py --data data/data.yaml --epochs 100 --batch 16 --device 0
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def train(
    data_yaml: str = "data/data.yaml",
    epochs: int = 100,
    batch: int = 16,
    imgsz: int = 640,
    device: str = "cpu",
    project: str = "training/runs",
    name: str = "atm_surveillance",
    pretrained: str = "yolov8n.pt",
    lr0: float = 0.01,
    weight_decay: float = 0.0005,
    augment: bool = True,
    patience: int = 20,
) -> str:
    """
    Train a YOLOv8 nano model.

    Args:
        data_yaml: Path to the dataset YAML file.
        epochs: Number of training epochs.
        batch: Batch size.
        imgsz: Input image size (square).
        device: Training device ("cpu", "0", "0,1", …).
        project: Output project directory.
        name: Run name (subdirectory under *project*).
        pretrained: Pre-trained weights file to start from.
        lr0: Initial learning rate.
        weight_decay: L2 regularisation factor.
        augment: Enable built-in augmentation.
        patience: Early stopping patience (epochs).

    Returns:
        Path to the best model weights.
    """
    try:
        from ultralytics import YOLO  # type: ignore[import]
    except ImportError:
        raise RuntimeError("ultralytics not installed. Run: pip install ultralytics")

    model = YOLO(pretrained)

    results = model.train(
        data=data_yaml,
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        device=device,
        project=project,
        name=name,
        lr0=lr0,
        weight_decay=weight_decay,
        augment=augment,
        patience=patience,
        save=True,
        plots=True,
        verbose=True,
    )

    best_weights = os.path.join(project, name, "weights", "best.pt")
    print(f"\nTraining complete. Best weights: {best_weights}")
    return best_weights


def main() -> None:
    parser = argparse.ArgumentParser(description="Train YOLOv8 ATM surveillance model")
    parser.add_argument("--data", default="data/data.yaml")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--project", default="training/runs")
    parser.add_argument("--name", default="atm_surveillance")
    parser.add_argument("--pretrained", default="yolov8n.pt")
    parser.add_argument("--patience", type=int, default=20)
    args = parser.parse_args()

    train(
        data_yaml=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        project=args.project,
        name=args.name,
        pretrained=args.pretrained,
        patience=args.patience,
    )


if __name__ == "__main__":
    main()
