"""
Model export script.

Exports a trained YOLOv8 model to ONNX format for optimised inference
on Raspberry Pi (using OpenCV DNN or ONNX Runtime).

Usage::

    python training/export_model.py --model training/runs/atm_surveillance/weights/best.pt
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def export_onnx(
    model_path: str,
    output_dir: str = "models",
    imgsz: int = 640,
    simplify: bool = True,
    opset: int = 17,
    dynamic: bool = False,
) -> str:
    """
    Export a YOLOv8 model to ONNX.

    Args:
        model_path: Path to the .pt weights file.
        output_dir: Directory where the exported model will be placed.
        imgsz: Input image size for the ONNX graph.
        simplify: Whether to simplify the ONNX graph (requires onnxsim).
        opset: ONNX opset version.
        dynamic: Enable dynamic batch axis.

    Returns:
        Path to the exported ONNX model.
    """
    try:
        from ultralytics import YOLO  # type: ignore[import]
    except ImportError:
        raise RuntimeError("ultralytics not installed.")

    model = YOLO(model_path)
    export_path = model.export(
        format="onnx",
        imgsz=imgsz,
        simplify=simplify,
        opset=opset,
        dynamic=dynamic,
    )

    # Copy to output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    dst = os.path.join(output_dir, "atm_surveillance.onnx")
    if export_path and os.path.isfile(export_path):
        import shutil
        shutil.copy2(export_path, dst)
        print(f"ONNX model exported to {dst}")
    else:
        dst = str(export_path)

    return dst


def main() -> None:
    parser = argparse.ArgumentParser(description="Export YOLOv8 model to ONNX")
    parser.add_argument("--model", required=True, help="Path to best.pt")
    parser.add_argument("--output-dir", default="models")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument(
        "--no-simplify", action="store_true", help="Disable ONNX graph simplification"
    )
    args = parser.parse_args()

    export_onnx(
        model_path=args.model,
        output_dir=args.output_dir,
        imgsz=args.imgsz,
        simplify=not args.no_simplify,
        opset=args.opset,
    )


if __name__ == "__main__":
    main()
