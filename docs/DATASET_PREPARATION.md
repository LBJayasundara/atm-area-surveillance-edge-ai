# Dataset Preparation Guide

## Dataset Sources

| Class | Source | Link |
|-------|--------|------|
| gun | Roboflow Universe — `pistols-cto8y` | https://universe.roboflow.com/roboflow-100/pistols-cto8y |
| knife | Roboflow Universe — `knife-detection-bjhxp` | https://universe.roboflow.com/roboflow-100/knife-detection-bjhxp |
| helmet | Roboflow Universe — `hard-hat-workers-pdblr` | https://universe.roboflow.com/hardhat-universe/hard-hat-workers-pdblr |
| mask | Roboflow Universe — `face-mask-detection-tznmi` | https://universe.roboflow.com/roboflow-100/face-mask-detection-tznmi |

## Automated Download (Roboflow API)

```bash
export ROBOFLOW_API_KEY="your_api_key"
python data/prepare_dataset.py
```

## Manual Download

```bash
python data/prepare_dataset.py --manual
```

Follow the printed instructions to manually download and place datasets.

## YOLO Format

Each dataset should follow:

```
<class_name>/
  images/
    train/  *.jpg
    val/    *.jpg
  labels/
    train/  *.txt    # class cx cy w h (normalised)
    val/    *.txt
```

## Merge Datasets

```bash
python data/merge_datasets.py
```

This remaps class IDs: gun→0, knife→1, helmet→2, mask→3.

## Validate

```bash
python data/validate_dataset.py
```

## Augmentation

YOLOv8 applies augmentation automatically during training:
- Mosaic, random flip, scale, HSV jitter
- Set `augment: true` in `training/train.py` (default)
