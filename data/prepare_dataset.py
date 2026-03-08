"""
Dataset preparation script.

Downloads publicly available weapon and face-concealment datasets and
organises them into the expected directory layout:

    data/
      raw/
        gun/         ← downloaded gun dataset
        knife/       ← downloaded knife dataset
        helmet/      ← downloaded helmet dataset
        mask/        ← downloaded mask dataset

Usage::

    python data/prepare_dataset.py --output data/raw

Note: Requires a Roboflow API key exported as ROBOFLOW_API_KEY, or manually
place datasets in data/raw/<class_name>/ following YOLO format.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def download_roboflow_dataset(
    workspace: str,
    project: str,
    version: int,
    api_key: str,
    output_dir: str,
    fmt: str = "yolov8",
) -> str:
    """
    Download a Roboflow dataset using the roboflow SDK.

    Args:
        workspace: Roboflow workspace slug.
        project: Project slug.
        version: Dataset version number.
        api_key: Roboflow API key.
        output_dir: Directory where the dataset will be saved.
        fmt: Download format (default "yolov8").

    Returns:
        Local path to the downloaded dataset directory.
    """
    try:
        import roboflow  # type: ignore[import]
    except ImportError:
        print("Install roboflow: pip install roboflow")
        sys.exit(1)

    rf = roboflow.Roboflow(api_key=api_key)
    project_obj = rf.workspace(workspace).project(project)
    dataset = project_obj.version(version).download(fmt, location=output_dir)
    return dataset.location


def manual_instructions() -> None:
    """Print manual dataset preparation instructions."""
    print(
        """
Manual Dataset Preparation
==========================
Download the following datasets from Roboflow Universe or Kaggle, then
place them in data/raw/ following YOLO format (images/ and labels/ subdirs):

1. Gun detection:
   https://universe.roboflow.com/roboflow-100/pistols-cto8y
   → data/raw/gun/

2. Knife detection:
   https://universe.roboflow.com/roboflow-100/knife-detection-bjhxp
   → data/raw/knife/

3. Helmet detection:
   https://universe.roboflow.com/hardhat-universe/hard-hat-workers-pdblr
   → data/raw/helmet/

4. Mask detection:
   https://universe.roboflow.com/roboflow-100/face-mask-detection-tznmi
   → data/raw/mask/

Each dataset directory should contain:
  images/
    train/  val/  (test/)
  labels/
    train/  val/  (test/)
"""
    )


def main() -> None:
    """Entry point for dataset preparation."""
    parser = argparse.ArgumentParser(description="Prepare ATM surveillance datasets")
    parser.add_argument("--output", default="data/raw", help="Output directory")
    parser.add_argument("--api-key", default=os.environ.get("ROBOFLOW_API_KEY", ""))
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Print manual download instructions",
    )
    args = parser.parse_args()

    if args.manual or not args.api_key:
        manual_instructions()
        return

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    datasets = [
        ("roboflow-100", "pistols-cto8y", 2, "gun"),
        ("roboflow-100", "knife-detection-bjhxp", 1, "knife"),
        ("hardhat-universe", "hard-hat-workers-pdblr", 15, "helmet"),
        ("roboflow-100", "face-mask-detection-tznmi", 1, "mask"),
    ]

    for workspace, project, version, name in datasets:
        out_dir = str(output / name)
        print(f"Downloading {name} dataset…")
        try:
            path = download_roboflow_dataset(
                workspace, project, version, args.api_key, out_dir
            )
            print(f"  ✓ Saved to {path}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ Failed: {exc}")

    print("\nDataset preparation complete. Run merge_datasets.py next.")


if __name__ == "__main__":
    main()
