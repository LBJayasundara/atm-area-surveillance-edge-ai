"""
Dataset validation script.

Checks the merged dataset for:
- Missing image files for label files
- Missing label files for image files
- Invalid bounding boxes
- Class distribution summary

Usage::

    python data/validate_dataset.py --dataset data/merged_dataset
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Dict, List

CLASS_NAMES = {0: "gun", 1: "knife", 2: "helmet", 3: "mask"}
SPLITS = ["train", "val", "test"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def validate_label_file(label_path: Path) -> List[str]:
    """
    Validate a single YOLO label file.

    Args:
        label_path: Path to the .txt label file.

    Returns:
        List of error/warning strings (empty means valid).
    """
    errors: List[str] = []
    for i, line in enumerate(label_path.read_text().splitlines()):
        parts = line.strip().split()
        if not parts:
            continue
        if len(parts) != 5:
            errors.append(f"Line {i + 1}: expected 5 values, got {len(parts)}")
            continue
        try:
            cls = int(parts[0])
            cx, cy, w, h = map(float, parts[1:])
        except ValueError as exc:
            errors.append(f"Line {i + 1}: parse error — {exc}")
            continue
        if cls not in CLASS_NAMES:
            errors.append(f"Line {i + 1}: unknown class id {cls}")
        for name, val in [("cx", cx), ("cy", cy), ("w", w), ("h", h)]:
            if not (0.0 <= val <= 1.0):
                errors.append(
                    f"Line {i + 1}: {name}={val:.4f} out of [0, 1] range"
                )
    return errors


def validate_split(dataset_root: Path, split: str) -> Dict:
    """
    Validate a single dataset split.

    Args:
        dataset_root: Root of the merged dataset.
        split: Split name ("train", "val", or "test").

    Returns:
        Dictionary with validation results.
    """
    img_dir = dataset_root / "images" / split
    lbl_dir = dataset_root / "labels" / split

    if not img_dir.exists():
        return {"split": split, "status": "missing"}

    images = {p.stem: p for p in img_dir.iterdir() if p.suffix in IMAGE_EXTENSIONS}
    labels = {p.stem: p for p in lbl_dir.iterdir() if p.suffix == ".txt"} if lbl_dir.exists() else {}

    missing_labels = [stem for stem in images if stem not in labels]
    missing_images = [stem for stem in labels if stem not in images]

    class_counts: Counter = Counter()
    file_errors: Dict[str, List[str]] = {}

    for stem, lbl_path in labels.items():
        errs = validate_label_file(lbl_path)
        if errs:
            file_errors[lbl_path.name] = errs
        for line in lbl_path.read_text().splitlines():
            parts = line.strip().split()
            if parts:
                try:
                    class_counts[int(parts[0])] += 1
                except ValueError:
                    pass

    return {
        "split": split,
        "images": len(images),
        "labels": len(labels),
        "missing_labels": missing_labels[:10],  # show first 10 only
        "missing_images": missing_images[:10],
        "class_distribution": {CLASS_NAMES.get(c, str(c)): n for c, n in sorted(class_counts.items())},
        "file_errors": file_errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate merged YOLO dataset")
    parser.add_argument("--dataset", default="data/merged_dataset")
    args = parser.parse_args()

    root = Path(args.dataset)
    if not root.exists():
        print(f"Dataset not found at {root}")
        return

    overall_ok = True
    for split in SPLITS:
        result = validate_split(root, split)
        print(f"\n[{split}]")
        if result.get("status") == "missing":
            print("  Not present — skipping.")
            continue
        print(f"  Images : {result['images']}")
        print(f"  Labels : {result['labels']}")
        if result["missing_labels"]:
            print(f"  ⚠ Missing labels: {result['missing_labels']}")
            overall_ok = False
        if result["missing_images"]:
            print(f"  ⚠ Missing images: {result['missing_images']}")
            overall_ok = False
        print(f"  Class distribution: {result['class_distribution']}")
        if result["file_errors"]:
            print(f"  ✗ Files with errors ({len(result['file_errors'])}):")
            for fname, errs in list(result["file_errors"].items())[:5]:
                print(f"    {fname}: {errs[0]}")
            overall_ok = False

    print("\n" + ("✓ Dataset is valid." if overall_ok else "✗ Validation issues found."))


if __name__ == "__main__":
    main()
