"""
Model evaluation script.

Evaluates a trained YOLOv8 model on the validation set and prints
precision, recall, mAP@50, and mAP@50-95 metrics.

Usage::

    python training/evaluate.py --model training/runs/atm_surveillance/weights/best.pt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def evaluate(
    model_path: str,
    data_yaml: str = "data/data.yaml",
    imgsz: int = 640,
    device: str = "cpu",
    split: str = "val",
    output_json: str = "training/metrics.json",
) -> dict:
    """
    Evaluate a trained model.

    Args:
        model_path: Path to the .pt model file.
        data_yaml: Dataset YAML file.
        imgsz: Inference image size.
        device: Compute device.
        split: Dataset split to evaluate on ("val" or "test").
        output_json: Where to save the metrics JSON.

    Returns:
        Dictionary of evaluation metrics.
    """
    try:
        from ultralytics import YOLO  # type: ignore[import]
    except ImportError:
        raise RuntimeError("ultralytics not installed.")

    model = YOLO(model_path)
    results = model.val(
        data=data_yaml,
        imgsz=imgsz,
        device=device,
        split=split,
        verbose=True,
    )

    metrics = {
        "precision": float(results.box.mp),
        "recall": float(results.box.mr),
        "mAP50": float(results.box.map50),
        "mAP50_95": float(results.box.map),
    }

    Path(output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).write_text(json.dumps(metrics, indent=2))

    print("\nEvaluation Results:")
    for key, value in metrics.items():
        print(f"  {key:12s}: {value:.4f}")
    print(f"\nMetrics saved to {output_json}")

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate ATM surveillance model")
    parser.add_argument("--model", required=True, help="Path to .pt model")
    parser.add_argument("--data", default="data/data.yaml")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--split", default="val", choices=["val", "test"])
    parser.add_argument("--output", default="training/metrics.json")
    args = parser.parse_args()

    evaluate(
        model_path=args.model,
        data_yaml=args.data,
        imgsz=args.imgsz,
        device=args.device,
        split=args.split,
        output_json=args.output,
    )


if __name__ == "__main__":
    main()
