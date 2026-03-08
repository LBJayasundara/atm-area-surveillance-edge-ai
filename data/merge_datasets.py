"""
Dataset merge script.

Combines individual class datasets (gun, knife, helmet, mask) into a
single YOLO-format dataset with unified class IDs:

    0 → gun
    1 → knife
    2 → helmet
    3 → mask

Input structure (per class)::

    data/raw/<class>/
      images/train/*.jpg
      images/val/*.jpg
      labels/train/*.txt   ← original class 0 labels
      labels/val/*.txt

Output structure::

    data/merged_dataset/
      images/train/
      images/val/
      images/test/
      labels/train/
      labels/val/
      labels/test/

Usage::

    python data/merge_datasets.py
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path
from typing import List

CLASS_NAMES = ["gun", "knife", "helmet", "mask"]
SPLITS = ["train", "val", "test"]


def remap_label_file(src: Path, dst: Path, new_class_id: int) -> None:
    """
    Copy a YOLO label file, replacing the class ID on every line.

    Args:
        src: Source label file path.
        dst: Destination label file path.
        new_class_id: Target class ID to write.
    """
    lines: List[str] = []
    for line in src.read_text().splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        parts[0] = str(new_class_id)
        lines.append(" ".join(parts))
    dst.write_text("\n".join(lines) + "\n")


def merge(input_dir: str, output_dir: str) -> None:
    """
    Merge per-class datasets into one unified dataset.

    Args:
        input_dir: Root directory containing per-class subdirectories.
        output_dir: Destination merged dataset directory.
    """
    out_root = Path(output_dir)

    # Create output directories
    for split in SPLITS:
        (out_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (out_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    counters = {split: 0 for split in SPLITS}

    for class_id, class_name in enumerate(CLASS_NAMES):
        class_dir = Path(input_dir) / class_name
        if not class_dir.exists():
            print(f"  Warning: {class_dir} not found — skipping.")
            continue

        for split in SPLITS:
            img_dir = class_dir / "images" / split
            lbl_dir = class_dir / "labels" / split

            if not img_dir.exists():
                continue

            image_files = sorted(img_dir.glob("*.[jJpP][pPnN][gG]*"))
            for img_path in image_files:
                # Build unique filename to avoid collisions
                stem = f"{class_name}_{img_path.stem}"
                out_img = out_root / "images" / split / (stem + img_path.suffix)
                shutil.copy2(img_path, out_img)

                # Corresponding label
                lbl_path = lbl_dir / (img_path.stem + ".txt")
                out_lbl = out_root / "labels" / split / (stem + ".txt")
                if lbl_path.exists():
                    remap_label_file(lbl_path, out_lbl, class_id)
                else:
                    # Create empty label file for images without annotations
                    out_lbl.write_text("")

                counters[split] += 1

    print("\nMerge complete:")
    for split, count in counters.items():
        print(f"  {split}: {count} images")
    print(f"\nOutput → {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge class datasets for ATM surveillance")
    parser.add_argument("--input", default="data/raw", help="Per-class dataset root")
    parser.add_argument("--output", default="data/merged_dataset", help="Merged output dir")
    args = parser.parse_args()
    merge(args.input, args.output)


if __name__ == "__main__":
    main()
